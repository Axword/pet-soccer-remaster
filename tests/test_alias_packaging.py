"""Builder and native alias-delta tests on synthetic files; never a game or UI."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
import build_public_package as package
import delta

HIDDEN = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
NATIVE_CASES = []
SHA = lambda data: hashlib.sha256(data).hexdigest()


class AliasBuilderTests(unittest.TestCase):
    def setUp(self):
        fixtures = ROOT / 'tests/alias-fixtures'
        fixtures.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=fixtures, prefix='builder-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / 'source'
        self.profile = self.root / 'profile'
        self.base.mkdir(); (self.profile / 'payload').mkdir(parents=True)
        self.base_bytes = bytes(range(256)) * 8
        (self.base / 'stock.bin').write_bytes(self.base_bytes)
        self.manifest = self.root / 'base.tsv'
        self.manifest.write_text(SHA(self.base_bytes) + '\tstock.bin\n', encoding='utf8')

    def prepare(self, targets, mapping=None, raw_mapping=None):
        rows = []
        for name, data in targets.items():
            file = self.profile / 'payload' / name
            file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(data)
            rows.append(SHA(data) + '\t' + name + '\n')
        (self.profile / 'payload.tsv').write_text(''.join(rows), encoding='utf8')
        if mapping is not None or raw_mapping is not None:
            self.mapping = self.root / 'source-map.json'
            self.mapping.write_text(raw_mapping if raw_mapping is not None else json.dumps(mapping), encoding='utf8')
        else:
            self.mapping = None

    def build(self, succeeds=True):
        out = self.root / 'package'
        args = [sys.executable, '-B', ROOT / 'build_public_package.py', '--base-game', self.base,
                '--base-manifest', self.manifest, '--mod-profile', self.profile, '--output', out]
        if self.mapping is not None: args += ['--source-map', self.mapping]
        p = subprocess.run(list(map(str, args)), capture_output=True, creationflags=HIDDEN)
        self.assertEqual(p.returncode == 0, succeeds, (p.stdout + p.stderr).decode('utf8', 'replace'))
        self.assertEqual((self.base / 'stock.bin').read_bytes(), self.base_bytes)
        return out

    def test_identical_alias_is_materialized_as_copy_delta(self):
        self.prepare({'new/deep/alias.bin': self.base_bytes}, {'new/deep/alias.bin': 'stock.bin'})
        out = self.build(); rows = (out / 'patches.tsv').read_text().strip().split('\t')
        self.assertEqual(len(rows), 6); self.assertEqual(rows[5], 'stock.bin')
        stream = (out / 'payload' / rows[4]).read_bytes()
        self.assertEqual(delta.apply(self.base_bytes, stream), self.base_bytes)
        self.assertFalse((out / 'payload/new/deep/alias.bin').exists())
        self.assertEqual(json.loads((out / 'manifest.json').read_text())['alias_delta_files'], 1)

    def test_changed_alias_and_legacy_patch_emit_mixed_six_and_five_columns(self):
        target = self.base_bytes[:700] + b'modification' + self.base_bytes[707:]
        self.prepare({'stock.bin': target, 'aliases/new.bin': target}, {'aliases/new.bin': 'stock.bin'})
        out = self.build(); lines = [x.split('\t') for x in (out / 'patches.tsv').read_text().splitlines()]
        self.assertEqual(sorted(map(len, lines)), [5, 6])
        for row in lines:self.assertEqual(delta.apply(self.base_bytes, (out / 'payload' / row[4]).read_bytes()), target)

    def test_unchanged_same_path_is_omitted(self):
        self.prepare({'stock.bin': self.base_bytes}, {'stock.bin': 'STOCK.BIN'})
        out = self.build(); self.assertEqual((out / 'patches.tsv').read_bytes(), b'')
        self.assertEqual(len(json.loads((out / 'manifest.json').read_text())['omitted_unchanged_originals']), 1)

    def test_code_archive_alias_normalizes_both_streams(self):
        def archive(path, text):
            with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:z.writestr('owned.txt', text)
            return path.read_bytes()
        original = archive(self.base / 'code.pak', b'original fixture')
        target = archive(self.root / 'fixture.zip', b'changed fixture')
        self.manifest.write_text(self.manifest.read_text() + SHA(original) + '\tcode.pak\n', encoding='utf8')
        self.prepare({'aliases/code-copy.pak': target}, {'aliases/code-copy.pak': 'code.pak'})
        out = self.build(); row = (out / 'patches.tsv').read_text().strip().split('\t')
        result = delta.apply(delta.normalize_zip(original), (out / 'payload' / row[4]).read_bytes())
        self.assertEqual(result, delta.normalize_zip(target)); self.assertEqual((self.base / 'code.pak').read_bytes(), original)

    def test_source_map_rejects_unknown_source(self):
        self.prepare({'alias.bin': b'new'}, {'alias.bin': 'not-stock.bin'}); self.build(False)

    def test_source_map_cannot_chain_new_aliases(self):
        self.prepare({'a.bin': b'a', 'b.bin': b'b'}, {'a.bin': 'stock.bin', 'b.bin': 'a.bin'}); self.build(False)

    def test_source_map_rejects_unused_target(self):
        self.prepare({'alias.bin': b'new'}, {'unused.bin': 'stock.bin'}); self.build(False)

    def test_source_map_rejects_duplicate_json_keys(self):
        self.prepare({'alias.bin': b'new'}, raw_mapping='{"alias.bin":"stock.bin","alias.bin":"stock.bin"}'); self.build(False)

    def test_source_map_rejects_case_slash_duplicate_targets(self):
        self.prepare({'dir/alias.bin': b'new'}, raw_mapping='{"dir/alias.bin":"stock.bin","DIR\\\\ALIAS.BIN":"stock.bin"}'); self.build(False)

    def test_source_map_rejects_non_object_and_non_string_values(self):
        self.prepare({'alias.bin': b'new'}, raw_mapping='["stock.bin"]'); self.build(False)
        self.mapping.write_text('{"alias.bin": 123}', encoding='utf8'); self.build(False)

    def test_source_map_rejects_unsafe_sources(self):
        for value in ['../stock.bin', '/stock.bin', 'C:/stock.bin', 'stock.bin:stream', 'dir//stock.bin', 'CON.txt']:
            with self.subTest(value=value):
                original = {'stock.bin': ('0' * 64, 'stock.bin')}
                file = self.root / 'bad.json'; file.write_text(json.dumps({'alias.bin': value}), encoding='utf8')
                with self.assertRaises(ValueError): package.source_mapping(file, original, [('1' * 64, 'alias.bin')])

    def test_manifest_rejects_duplicate_and_reserved_targets(self):
        file = self.root / 'duplicate.tsv'; file.write_text('0' * 64 + '\tdir/alias.bin\n' + '1' * 64 + '\tDIR\\ALIAS.BIN\n')
        with self.assertRaises(ValueError):package.rows(file)
        for name in ['.gmw-files.tsv', 'dir/Odinstaluj.exe', '.gmw-tools/own.bin', '.gmw-deltas/a.bin']:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):package.target_name(name)

    def test_physical_base_hash_mismatch_is_rejected(self):
        self.prepare({'alias.bin': b'new'}, {'alias.bin': 'stock.bin'})
        (self.base / 'stock.bin').write_bytes(b'wrong base')
        p = subprocess.run(list(map(str,[sys.executable,'-B',ROOT/'build_public_package.py','--base-game',self.base,'--base-manifest',self.manifest,'--mod-profile',self.profile,'--source-map',self.mapping,'--output',self.root/'package'])),capture_output=True,creationflags=HIDDEN)
        self.assertNotEqual(p.returncode, 0); self.assertEqual((self.base/'stock.bin').read_bytes(), b'wrong base')

    def test_readme_version_and_portable_python_paths(self):
        self.prepare({'CZYTAJ-GMW.txt': b'Wersja beta 0.1.0-beta.3. Kod moda.',
                      'online/runtime/python.exe': b'owned portable fixture',
                      'online/runtime/python3.dll': b'owned library fixture',
                      'online/runtime/python.zip': b'owned standard library fixture'})
        out=self.build()
        self.assertIn('Wersja beta 0.2.0-beta.1.',(out/'payload/CZYTAJ-GMW.txt').read_text(encoding='utf-8-sig'))
        for name in ['python.exe','python3.dll','python.zip']:
            self.assertTrue((out/'payload/online/runtime'/name).is_file())

    def test_builder_refuses_output_inside_original_or_profile(self):
        self.prepare({'alias.bin': b'new'}, {'alias.bin':'stock.bin'})
        for parent in [self.base,self.profile]:
            out=parent/'new-package'
            p=subprocess.run(list(map(str,[sys.executable,'-B',ROOT/'build_public_package.py','--base-game',self.base,'--base-manifest',self.manifest,'--mod-profile',self.profile,'--source-map',self.mapping,'--output',out])),capture_output=True,creationflags=HIDDEN)
            self.assertNotEqual(p.returncode,0);self.assertFalse(out.exists())
        self.assertEqual((self.base/'stock.bin').read_bytes(),self.base_bytes)


@unittest.skipUnless(os.name == 'nt', 'Native installer tests require Windows')
class AliasNativeTests(unittest.TestCase):
    def test_native_alias_matrix(self):
        helper = Path(os.environ.get('PETSOCCER_ALIAS_HELPER', str(ROOT/'installer/GMWInstallerHelper.exe'))).resolve()
        if not helper.is_file():self.skipTest('Compile installer/backend.cpp before native tests')
        fixtures = ROOT/'tests/alias-fixtures';fixtures.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixtures, prefix='native-') as temporary:
            root=Path(temporary);source=root/'source';payload=root/'payload';source.mkdir();(payload/'.gmw-deltas').mkdir(parents=True)
            base=bytes(range(256))*40; changed=base[:700]+b'new content'+base[710:]; other=b'other stock source'*128
            (source/'base.bin').write_bytes(base);(source/'other.bin').write_bytes(other)
            base_rows=SHA(base)+'\tbase.bin\n'+SHA(other)+'\tother.bin\n';(root/'base.tsv').write_text(base_rows)
            (payload/'mod.ini').write_bytes(b'[Mod]\nEnabled=1\n')
            mod_rows=SHA((payload/'mod.ini').read_bytes())+'\tmod.ini\n'
            streams={}
            for name,target in [('changed',changed),('identical',base)]:
                stream,_=delta.encode(base,target);streams[name]=stream;(payload/('.gmw-deltas/'+name+'.gmwd')).write_bytes(stream)
            def row(target='new/deep/alias.bin',kind='changed',source_name='base.bin',six=True):
                values=[SHA(base),SHA(changed if kind=='changed' else base),SHA(streams[kind]),target,'.gmw-deltas/'+kind+'.gmwd']
                if six:values.append(source_name)
                return '\t'.join(values)+'\n'
            def snapshot():return {str(p.relative_to(source)):p.read_bytes() for p in source.rglob('*') if p.is_file()}
            def case(name,rows,expected=None,mods=None,allowlist=None,patches=True,preserve=False):
                (root/'patches.tsv').write_text(rows);(root/'payload.tsv').write_text(mod_rows if mods is None else mods);(root/'base.tsv').write_text(base_rows if allowlist is None else allowlist)
                before=snapshot();dest=root/name
                command=[helper,'install',source,dest,payload,root/'base.tsv',root/'payload.tsv']
                if patches:command.append(root/'patches.tsv')
                p=subprocess.run(list(map(str,command)),capture_output=True,timeout=30,creationflags=HIDDEN)
                message=(p.stdout+p.stderr).decode('utf8','replace')
                self.assertEqual(p.returncode==0,expected is not None,(name,message))
                self.assertEqual(snapshot(),before,(name,'original source changed'))
                if expected is not None:
                    for rel,data in expected.items():self.assertEqual((dest/rel).read_bytes(),data,(name,rel))
                    ledger=(dest/'.gmw-files.tsv').read_text()
                    for rel in expected:self.assertIn(rel.replace('\\','/'),ledger)
                    if preserve:(dest/'new/deep/alias.bin').write_bytes(b'user modified alias');(dest/'user.txt').write_bytes(b'user data')
                    done=subprocess.run([str(helper),'uninstall',str(dest)],capture_output=True,timeout=30,creationflags=HIDDEN);self.assertEqual(done.returncode,0,done.stderr)
                    if preserve:
                        self.assertEqual((dest/'new/deep/alias.bin').read_bytes(),b'user modified alias');self.assertEqual((dest/'user.txt').read_bytes(),b'user data')
                    else:self.assertFalse(list(dest.rglob('*')),(name,'uninstall leftovers'))
                else:
                    self.assertFalse(dest.exists(),(name,'failed install committed'))
                    self.assertFalse(list(root.glob('.'+name+'.gmw-staging-*')),(name,'rollback leftovers'))
                self.assertEqual(snapshot(),before,(name,'uninstall changed original'))
                NATIVE_CASES.append(name)
            case('legacy5',row('base.bin',six=False),{'base.bin':changed})
            case('explicit6_same_path',row('base.bin'),{'base.bin':changed})
            case('new_nested_alias',row(),{'new/deep/alias.bin':changed})
            case('identical_alias',row(kind='identical'),{'new/deep/alias.bin':base})
            first=row('base.bin',six=False);alias=row('aliases/original.bin',kind='identical')
            case('patch_order_forward',first+alias,{'base.bin':changed,'aliases/original.bin':base})
            case('patch_order_reverse',alias+first,{'base.bin':changed,'aliases/original.bin':base})
            (payload/'base.bin').write_bytes(b'standalone overlay')
            case('source_ignores_standalone_overlay',row(),{'base.bin':b'standalone overlay','new/deep/alias.bin':changed},mods=mod_rows+SHA(b'standalone overlay')+'\tbase.bin\n')
            case('legacy_without_patch_list','',{'base.bin':base},patches=False)
            case('preserve_modified_alias',row(),{'new/deep/alias.bin':changed},preserve=True)
            for name,path in [('source_traversal','../base.bin'),('source_absolute',str(source/'base.bin')),('source_ads','base.bin:stream'),('source_empty_component','dir//base.bin'),('source_device','NUL.txt'),('source_not_allowlisted','not-stock.bin')]:case(name,row(source_name=path))
            for name,path in [('target_traversal','../alias.bin'),('target_absolute',str(root/'escape.bin')),('target_ads','alias.bin:stream'),('target_reserved','.gmw-owner.txt'),('target_reserved_nested','new/Odinstaluj.exe'),('target_tooldir','.gmw-tools/alias.bin'),('target_device','CON.txt')]:case(name,row(target=path))
            for name,path in [('device_con_multiple_extensions','CON.foo.bar'),('device_nul_multiple_extensions','new/NUL.a.b'),('device_com_multiple_extensions','COM1.a.b')]:case(name,row(target=path))
            case('case_slash_duplicate_target',row('new/alias.bin')+row('NEW\\ALIAS.BIN'))
            case('standalone_collision',row('MOD.INI'))
            case('wrong_source_manifest_hash',row().replace(SHA(base),'0'*64,1))
            case('wrong_delta_stream_hash',row().replace(SHA(streams['changed']),'0'*64))
            case('wrong_target_hash',row().replace(SHA(changed),'0'*64))
            line=row().strip().split('\t');case('four_columns','\t'.join(line[:4])+'\n');case('seven_columns','\t'.join(line+['extra'])+'\n');case('empty_sixth','\t'.join(line[:5])+'\t\n')
            (source/'base.bin').write_bytes(b'physically changed stock');case('physical_source_hash_mismatch',row());(source/'base.bin').write_bytes(base)
            (source/'other.bin').unlink();case('missing_original_source',row(source_name='other.bin').replace(SHA(base),SHA(other),1));(source/'other.bin').write_bytes(other)
            bad=streams['changed'][:-1];(payload/'.gmw-deltas/bad.gmwd').write_bytes(bad)
            late='\t'.join([SHA(base),SHA(changed),SHA(bad),'second/alias.bin','.gmw-deltas/bad.gmwd','base.bin'])+'\n'
            case('late_failure_rolls_back_alias_and_dirs',row()+late)
            link=source/'link';external=root/'external_stock';external.mkdir();(external/'base.bin').write_bytes(base)
            junction=False;linked=False
            try:
                os.symlink(str(external),str(link),target_is_directory=True);linked=True
            except OSError:
                # Directory junctions do not require the symbolic-link privilege.
                self.assertTrue(link.resolve().is_relative_to(root.resolve()))
                self.assertTrue(external.resolve().is_relative_to(root.resolve()))
                created=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(link),str(external)],capture_output=True,creationflags=HIDDEN)
                linked=created.returncode==0;junction=linked
            if linked:
                try:
                    # Source manifest would otherwise allow the same real bytes via a link.
                    case('source_reparse_refused',row(source_name='link/base.bin'),allowlist=base_rows+SHA(base)+'\tlink/base.bin\n')
                finally:
                    if junction:os.rmdir(link)
                    else:link.unlink()
            else:print('NATIVE_ALIAS_REPARSE_SKIPPED cannot create isolated test link')
        print('NATIVE_ALIAS_CASES='+str(len(NATIVE_CASES)))


if __name__ == '__main__':unittest.main()
