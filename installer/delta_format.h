// GMWDLT1: verified copy/literal deltas. Original game bytes are read locally.
// Included after the backend's path, hashing and journaling helpers.
#include <cstdint>
#include <cstring>

struct PatchEntry {
    std::string base_hash, target_hash, delta_hash;
    fs::path relative, delta_relative;
};
static bool valid_digest(const std::string& value) {
    return value.size() == 64 && value.find_first_not_of("0123456789abcdef") == std::string::npos;
}
static void safe_patch_name(const fs::path& path) {
    auto leaf = lower(path.filename().wstring());
    require(leaf != L".gmw-files.tsv" && leaf != L".gmw-owner.txt" &&
        leaf != L"gmwinstallerhelper.exe" && leaf != L"odinstaluj.exe", "Reserved patch destination");
}
static std::vector<PatchEntry> patch_manifest(const fs::path& file) {
    std::ifstream input(file, std::ios::binary);
    require(input.good(), "Required delta manifest is missing");
    std::vector<PatchEntry> result;
    std::set<std::wstring> seen;
    std::string line;
    while (std::getline(input, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty()) continue;
        std::istringstream row(line);
        std::vector<std::string> columns;
        std::string field;
        while (std::getline(row, field, '\t')) columns.push_back(field);
        require(columns.size() == 5, "Invalid delta manifest row");
        require(valid_digest(columns[0]) && valid_digest(columns[1]) && valid_digest(columns[2]), "Invalid delta digest");
        fs::path relative = relative_path(columns[3]), delta = relative_path(columns[4]);
        safe_patch_name(relative);
        require(seen.insert(lower(relative.wstring())).second, "Duplicate delta destination");
        require(lower(delta.begin()->wstring()) == L".gmw-deltas", "Delta must be inside the package delta directory");
        result.push_back({columns[0], columns[1], columns[2], relative, delta});
    }
    return result;
}
static void delta_read(std::istream& input, char* buffer, size_t count) {
    input.read(buffer, static_cast<std::streamsize>(count));
    require(static_cast<size_t>(input.gcount()) == count, "Truncated delta stream");
}
static std::uint64_t delta_u64(std::istream& input) {
    unsigned char data[8]; delta_read(input, reinterpret_cast<char*>(data), 8);
    std::uint64_t value = 0;
    for (int i = 0; i < 8; ++i) value |= static_cast<std::uint64_t>(data[i]) << (8 * i);
    return value;
}
static std::string delta_digest(std::istream& input) {
    unsigned char bytes[32]; delta_read(input, reinterpret_cast<char*>(bytes), 32);
    std::ostringstream text; text << std::hex << std::setfill('0');
    for (unsigned char value : bytes) text << std::setw(2) << static_cast<unsigned>(value);
    return text.str();
}
static std::wstring quote_argument(const fs::path& value) {
    std::wstring result = L"\""; size_t slashes = 0;
    for (wchar_t c : value.wstring()) {
        if (c == L'\\') { ++slashes; continue; }
        result.append(c == L'\"' ? slashes * 2 + 1 : slashes, L'\\');
        result += c; slashes = 0;
    }
    result.append(slashes * 2, L'\\'); return result + L"\"";
}
static void normalize_code_zip(const fs::path& input, const fs::path& output,
                               const fs::path& payload, const fs::path& stage) {
    fs::path java = stage / L"jre/bin/java.exe", helper = payload / L".gmw-tools/GMWZipNormalize.class";
    ordinary_path(java); ordinary_path(helper);
    require(fs::is_regular_file(java) && fs::is_regular_file(helper), "ZIP normalization helper is missing");
    require(sha256(helper) == "100bc5030aba432464cd12ec97ab5f3b78b88da8bac23cd5b4299e60587120b0", "ZIP helper verification failed");
    std::wstring command = quote_argument(java) + L" -Xmx64m -cp " + quote_argument(helper.parent_path()) +
        L" GMWZipNormalize " + quote_argument(input) + L" " + quote_argument(output);
    STARTUPINFOW startup = {}; startup.cb = sizeof(startup);
    PROCESS_INFORMATION process = {};
    require(CreateProcessW(java.c_str(), &command[0], nullptr, nullptr, FALSE, CREATE_NO_WINDOW,
            nullptr, stage.c_str(), &startup, &process) != 0, "Cannot start the installed game's ZIP helper");
    DWORD wait = WaitForSingleObject(process.hProcess, 30000), exit_code = 1;
    if (wait == WAIT_OBJECT_0) GetExitCodeProcess(process.hProcess, &exit_code);
    else { TerminateProcess(process.hProcess, 1); WaitForSingleObject(process.hProcess, 5000); }
    CloseHandle(process.hThread); CloseHandle(process.hProcess);
    require(wait == WAIT_OBJECT_0 && exit_code == 0 && fs::is_regular_file(output), "Original ZIP normalization failed");
}
static void apply_delta(const PatchEntry& row, const fs::path& payload, const fs::path& stage,
                        std::vector<fs::path>& files) {
    const std::uint64_t maximum_size = 1024ULL * 1024 * 1024;
    fs::path destination = stage / row.relative, delta_path = payload / row.delta_relative;
    require(within(destination, stage) && within(delta_path, payload), "Delta path outside owned roots");
    ordinary_path(destination); ordinary_path(delta_path);
    require(fs::is_regular_file(destination) && fs::is_regular_file(delta_path), "Delta input is missing");
    require(fs::file_size(delta_path) <= maximum_size, "Delta stream exceeds supported size");
    require(sha256(destination) == row.base_hash, "Delta requires the supported original game file");
    require(sha256(delta_path) == row.delta_hash, "Delta stream verification failed");
    fs::path base_path = destination;
    if (lower(row.relative.wstring()) == L"code.pak") {
        base_path += L".gmwbase.tmp";
        require(!fs::exists(base_path), "ZIP base temporary path is occupied");
        files.push_back(base_path);
        normalize_code_zip(destination, base_path, payload, stage);
    }
    std::ifstream input(delta_path, std::ios::binary);
    char magic[8]; delta_read(input, magic, 8);
    require(std::memcmp(magic, "GMWDLT1\0", 8) == 0, "Unsupported delta stream");
    std::uint64_t base_size = delta_u64(input), target_size = delta_u64(input);
    require(base_size <= maximum_size && target_size <= maximum_size && base_size == fs::file_size(base_path), "Invalid delta file size");
    require(delta_digest(input) == sha256(base_path) && delta_digest(input) == row.target_hash, "Delta header does not match manifest");
    fs::path temporary = destination; temporary += L".gmwpatch.tmp";
    require(!fs::exists(temporary) && within(temporary, stage), "Delta temporary path is occupied");
    files.push_back(temporary);
    std::ifstream base(base_path, std::ios::binary);
    std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
    require(base.good() && output.good(), "Cannot open delta files");
    std::uint64_t produced = 0;
    char buffer[128 * 1024];
    while (true) {
        int command = input.get();
        require(command != std::char_traits<char>::eof(), "Delta lacks end command");
        if (command == 255) break;
        require(command == 0 || command == 1, "Unknown delta command");
        std::uint64_t offset = command == 0 ? delta_u64(input) : 0;
        std::uint64_t length = delta_u64(input);
        require(length > 0 && length <= target_size - produced, "Delta output exceeds declared bounds");
        if (command == 0) {
            require(offset <= base_size && length <= base_size - offset, "Delta copy exceeds original file");
            base.clear(); base.seekg(static_cast<std::streamoff>(offset));
            require(base.good(), "Cannot seek original file");
        }
        for (std::uint64_t remaining = length; remaining;) {
            size_t count = static_cast<size_t>(std::min<std::uint64_t>(remaining, sizeof(buffer)));
            delta_read(command == 0 ? static_cast<std::istream&>(base) : static_cast<std::istream&>(input), buffer, count);
            output.write(buffer, static_cast<std::streamsize>(count));
            require(output.good(), "Cannot write patched game file");
            remaining -= count;
        }
        produced += length;
    }
    require(produced == target_size && input.peek() == std::char_traits<char>::eof(), "Delta stream length mismatch");
    output.close(); base.close();
    require(output.good() && sha256(temporary) == row.target_hash, "Patched game file verification failed");
    require(MoveFileExW(temporary.c_str(), destination.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0,
            "Cannot commit patched game file");
    if (base_path != destination) fs::remove(base_path);
}
