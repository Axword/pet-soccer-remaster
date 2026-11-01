#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <vector>
#include <map>
#include <set>
#include <algorithm>
#include <stdexcept>
#include <cwctype>

namespace fs = std::filesystem;
static const char* MAGIC = "PETSOCCER_GMW_20261031_V1";
struct Entry { std::string hash; fs::path relative; };

static void require(bool good, const char* text) { if (!good) throw std::runtime_error(text); }
static std::wstring lower(std::wstring value) {
    std::transform(value.begin(), value.end(), value.begin(), [](wchar_t c) { return (wchar_t)towlower(c); });
    return value;
}
static fs::path resolved_path(const fs::path& value) { return fs::weakly_canonical(fs::absolute(value)); }
static bool within(const fs::path& child, const fs::path& root) {
    auto c = lower(child.lexically_normal().wstring()), r = lower(root.lexically_normal().wstring());
    if (c == r) return true;
    if (!r.empty() && r.back() != L'\\') r += L'\\';
    return c.size() > r.size() && c.compare(0, r.size(), r) == 0;
}
static void ordinary_path(const fs::path& path) {
    require(path.is_absolute(), "Absolute path required");
    require(path.wstring().rfind(L"\\\\", 0) != 0, "Network/device paths are unsupported");
    fs::path current;
    for (const auto& part : path) {
        current /= part;
        DWORD attributes = GetFileAttributesW(current.c_str());
        if (attributes != INVALID_FILE_ATTRIBUTES)
            require((attributes & FILE_ATTRIBUTE_REPARSE_POINT) == 0, "Junction/symlink path refused");
    }
}
static fs::path relative_path(const std::string& value) {
    require(!value.empty() && value.find_first_of("\t\r\n:*") == std::string::npos, "Invalid relative file path");
    fs::path result = fs::u8path(value);
    require(!result.is_absolute() && !result.has_root_name(), "Rooted payload path refused");
    for (const auto& part : result) {
        std::wstring text = part.wstring();
        require(text != L"." && text != L".." && !text.empty(), "Traversal path refused");
        require(text.back() != L'.' && text.back() != L' ', "Ambiguous Windows file name");
    }
    return result;
}
static std::string sha256(const fs::path& file) {
    std::ifstream input(file, std::ios::binary);
    require(input.good(), "Cannot read a required file");
    BCRYPT_ALG_HANDLE algorithm = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    require(BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) == 0,
            "SHA256 provider unavailable");
    if (BCryptCreateHash(algorithm, &hash, nullptr, 0, nullptr, 0, 0) != 0) {
        BCryptCloseAlgorithmProvider(algorithm, 0);
        throw std::runtime_error("Cannot create SHA256 state");
    }
    char buffer[128 * 1024];
    while (input.read(buffer, sizeof(buffer)) || input.gcount()) {
        if (BCryptHashData(hash, reinterpret_cast<PUCHAR>(buffer), (ULONG)input.gcount(), 0) != 0) {
            BCryptDestroyHash(hash); BCryptCloseAlgorithmProvider(algorithm, 0);
            throw std::runtime_error("Cannot hash file data");
        }
    }
    require(input.eof(), "File read failed");
    unsigned char digest[32];
    NTSTATUS status = BCryptFinishHash(hash, digest, sizeof(digest), 0);
    BCryptDestroyHash(hash); BCryptCloseAlgorithmProvider(algorithm, 0);
    require(status == 0, "Cannot finish file hash");
    std::ostringstream result;
    result << std::hex << std::setfill('0');
    for (auto b : digest) result << std::setw(2) << (unsigned)b;
    return result.str();
}
static std::vector<Entry> manifest(const fs::path& file) {
    std::ifstream input(file, std::ios::binary);
    require(input.good(), "Required installation manifest is missing");
    std::string line;
    std::vector<Entry> result;
    std::set<std::wstring> seen;
    while (std::getline(input, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty()) continue;
        require(line.size() > 65 && line[64] == '\t', "Invalid manifest row");
        std::string digest = line.substr(0, 64);
        require(digest.find_first_not_of("0123456789abcdef") == std::string::npos, "Invalid manifest digest");
        fs::path path = relative_path(line.substr(65));
        auto leaf = lower(path.filename().wstring());
        require(leaf != L".gmw-files.tsv" && leaf != L".gmw-owner.txt" &&
                leaf != L"gmwinstallerhelper.exe" && leaf != L"odinstaluj.exe",
                "Installer-reserved file name in manifest");
        require(seen.insert(lower(path.wstring())).second, "Duplicate installation path");
        result.push_back({digest, path});
    }
    require(!result.empty(), "Installation manifest is empty");
    return result;
}
static void write_text(const fs::path& path, const std::string& value) {
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    out << value;
    out.close();
    require(out.good(), "Cannot write installation metadata");
}
static std::string read_text(const fs::path& path) {
    std::ifstream in(path, std::ios::binary);
    require(in.good(), "Installation metadata is missing");
    return std::string(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
}
static void create_inside(const fs::path& path, const fs::path& root, std::vector<fs::path>& created) {
    require(within(path, root), "Directory outside owned staging root");
    if (fs::exists(path)) { ordinary_path(path); return; }
    if (path != root) create_inside(path.parent_path(), root, created);
    fs::create_directory(path);
    created.push_back(path);
}
static void copy_verified(const fs::path& source, const fs::path& destination, const Entry& entry,
                          const fs::path& stage, std::vector<fs::path>& files, std::vector<fs::path>& dirs) {
    require(within(destination, stage), "Copy destination outside owned root");
    ordinary_path(source);
    require(fs::is_regular_file(source), "Required source file is missing");
    require(destination.wstring().size() < 250, "Installation path is too long for the game");
    create_inside(destination.parent_path(), stage, dirs);
    if (!fs::exists(destination)) files.push_back(destination);
    else SetFileAttributesW(destination.c_str(), FILE_ATTRIBUTE_NORMAL);
    fs::copy_file(source, destination, fs::copy_options::overwrite_existing);
    SetFileAttributesW(destination.c_str(), FILE_ATTRIBUTE_NORMAL);
    require(sha256(destination) == entry.hash, "File verification failed: wrong base version or damaged package");
}
#include "delta_format.h"
static void commit_stage(const fs::path& stage, const fs::path& target) {
    // Indexing/antivirus can briefly hold a freshly copied executable. Never replace an occupied target.
    for (int attempt = 0; attempt < 40; ++attempt) {
        require(!fs::exists(target), "Destination appeared during installation");
        if (MoveFileExW(stage.c_str(), target.c_str(), MOVEFILE_WRITE_THROUGH)) return;
        DWORD error = GetLastError();
        if ((error != ERROR_ACCESS_DENIED && error != ERROR_SHARING_VIOLATION && error != ERROR_LOCK_VIOLATION) || attempt == 39)
            throw std::system_error((int)error, std::system_category(), "Cannot finalize installation folder");
        Sleep(125);
    }
}
static int install(const fs::path& source_arg, const fs::path& target_arg, const fs::path& payload_arg,
                   const fs::path& base_manifest, const fs::path& payload_manifest, const fs::path& patch_list) {
    ordinary_path(fs::absolute(source_arg)); ordinary_path(fs::absolute(target_arg));
    ordinary_path(fs::absolute(payload_arg));
    fs::path source = resolved_path(source_arg), target = resolved_path(target_arg), payload = resolved_path(payload_arg);
    require(fs::is_directory(source) && fs::is_directory(payload), "Select the original Pet Soccer folder");
    require(!within(target, source) && !within(source, target), "Source and destination must be separate folders");
    require(!within(target, payload) && !within(payload, target), "Payload and destination overlap");
    require(target != target.root_path() && target.wstring().size() < 170, "Choose a shorter destination folder");
    require(!fs::exists(target), "Destination already exists: choose a new empty location");
    auto base = manifest(base_manifest), mod = manifest(payload_manifest);
    auto patches = patch_list.empty() ? std::vector<PatchEntry>() : patch_manifest(patch_list);
    std::map<std::wstring, std::string> original_hashes;
    std::set<std::wstring> mod_paths;
    for (const auto& row : base) original_hashes[lower(row.relative.wstring())] = row.hash;
    for (const auto& row : mod) mod_paths.insert(lower(row.relative.wstring()));
    for (const auto& row : patches) {
        auto key = lower(row.relative.wstring());
        require(original_hashes.count(key) && original_hashes.at(key) == row.base_hash, "Delta destination is not an original allowlisted file");
        require(!mod_paths.count(key), "Delta destination duplicates a standalone mod file");
        ordinary_path(payload / row.delta_relative);
        require(fs::is_regular_file(payload / row.delta_relative), "Delta file is missing");
    }
    // Manifests are generated from the supported stock PL edition. Never copy arbitrary source files.
    for (const auto& row : base) {
        ordinary_path(source / row.relative);
        require(fs::is_regular_file(source / row.relative), "Original game is incomplete");
    }
    for (const auto& row : mod) {
        ordinary_path(payload / row.relative);
        require(fs::is_regular_file(payload / row.relative), "Mod package is incomplete");
    }
    ordinary_path(target.parent_path());
    fs::create_directories(target.parent_path());
    fs::path stage = target.parent_path() / (L"." + target.filename().wstring() + L".gmw-staging-" + std::to_wstring(GetCurrentProcessId()));
    require(!fs::exists(stage) && within(stage, target.parent_path()), "Staging folder is already occupied");
    std::vector<fs::path> files, dirs;
    std::map<std::wstring, Entry> installed;
    try {
        require(CreateDirectoryW(stage.c_str(), nullptr) != 0, "Cannot exclusively create owned staging folder");
        dirs.push_back(stage);
        size_t count = 0;
        for (const auto& row : base) {
            copy_verified(source / row.relative, stage / row.relative, row, stage, files, dirs);
            installed[lower(row.relative.wstring())] = row;
            if (++count % 500 == 0) std::cout << "Verified base files: " << count << std::endl;
        }
        for (const auto& row : mod) {
            copy_verified(payload / row.relative, stage / row.relative, row, stage, files, dirs);
            installed[lower(row.relative.wstring())] = row;
        }
        for (const auto& row : patches) {
            apply_delta(row, payload, stage, files);
            installed[lower(row.relative.wstring())] = {row.target_hash, row.relative};
        }
        std::string ledger;
        for (const auto& pair : installed) ledger += pair.second.hash + "\t" + pair.second.relative.generic_u8string() + "\n";
        fs::path ledger_path = stage / L".gmw-files.tsv", marker = stage / L".gmw-owner.txt";
        files.push_back(ledger_path); files.push_back(marker);
        write_text(ledger_path, ledger);
        write_text(marker, std::string(MAGIC) + "\n" + target.generic_u8string() + "\n");
        commit_stage(stage, target);
        std::cout << "INSTALL_OK files=" << installed.size() << std::endl;
        return 0;
    } catch (...) {
        // Remove only exact files/directories created by this invocation, inside its checked staging root.
        for (auto it = files.rbegin(); it != files.rend(); ++it) {
            std::error_code ec;
            if (within(*it, stage)) { SetFileAttributesW(it->c_str(), FILE_ATTRIBUTE_NORMAL); fs::remove(*it, ec); }
        }
        for (auto it = dirs.rbegin(); it != dirs.rend(); ++it) {
            std::error_code ec;
            if (within(*it, stage)) fs::remove(*it, ec);
        }
        throw;
    }
}
static int uninstall(const fs::path& target_arg) {
    ordinary_path(fs::absolute(target_arg));
    fs::path target = resolved_path(target_arg);
    require(target != target.root_path(), "Refusing a filesystem root");
    std::string marker = read_text(target / L".gmw-owner.txt");
    require(marker == std::string(MAGIC) + "\n" + target.generic_u8string() + "\n", "This is not the owned mod installation");
    auto entries = manifest(target / L".gmw-files.tsv");
    // Validate the complete removal scope before deleting the first owned file.
    for (const auto& row : entries) {
        require(within(target / row.relative, target), "Uninstall path outside owned root");
        ordinary_path(target / row.relative);
    }
    std::set<fs::path> directories;
    size_t removed = 0, preserved = 0;
    for (const auto& row : entries) {
        fs::path file = target / row.relative;
        require(within(file, target), "Uninstall path outside owned root");
        ordinary_path(file);
        if (fs::exists(file)) {
            if (!fs::is_regular_file(file) || sha256(file) != row.hash) { ++preserved; continue; }
            SetFileAttributesW(file.c_str(), FILE_ATTRIBUTE_NORMAL);
            require(fs::remove(file), "Cannot remove a game file: close this mod copy first");
            ++removed;
        }
        for (fs::path parent = file.parent_path(); parent != target; parent = parent.parent_path()) {
            require(within(parent, target), "Uninstall parent outside owned root");
            directories.insert(parent);
        }
    }
    fs::remove(target / L".gmw-files.tsv"); fs::remove(target / L".gmw-owner.txt");
    std::vector<fs::path> ordered(directories.begin(), directories.end());
    std::sort(ordered.begin(), ordered.end(), [](const fs::path& a, const fs::path& b) { return a.wstring().size() > b.wstring().size(); });
    for (const auto& dir : ordered) { std::error_code ec; fs::remove(dir, ec); }
    std::cout << "UNINSTALL_OK removed=" << removed << " preserved_modified=" << preserved << std::endl;
    return 0;
}
int wmain(int argc, wchar_t** argv) {
    try {
        if ((argc == 7 || argc == 8) && std::wstring(argv[1]) == L"install")
            return install(argv[2], argv[3], argv[4], argv[5], argv[6], argc == 8 ? fs::path(argv[7]) : fs::path());
        if (argc == 3 && std::wstring(argv[1]) == L"uninstall") return uninstall(argv[2]);
        std::cerr << "Usage: helper install SOURCE TARGET PAYLOAD BASE_MANIFEST PAYLOAD_MANIFEST [PATCH_MANIFEST] | uninstall TARGET\n";
        return 2;
    } catch (const std::exception& e) {
        std::cerr << "INSTALLER_ERROR: " << e.what() << std::endl;
        return 1;
    }
}
