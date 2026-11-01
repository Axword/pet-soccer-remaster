"""Original recipe checks; optional external game input is never bundled.

Set PET_SOCCER_CODE_PAK to the reviewed beta2 mod archive and
PET_SOCCER_PREVIEW_HELPER to your own compiled CXHumanPreview.class.
These tests inspect transformed class files, not native rendering.
"""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys,tempfile,unittest,zipfile

from src.patches import human_preview as patch
from tools.classfile import ClassFile


class HumanPreviewRecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline=os.environ.get('PET_SOCCER_CODE_PAK')
        helper=os.environ.get('PET_SOCCER_PREVIEW_HELPER')
        if not baseline or not helper:
            raise unittest.SkipTest('Provide your external beta2 PAK and own compiled helper through the documented environment variables')
        cls.baseline=Path(baseline).resolve();cls.helper_path=Path(helper).resolve()
        with zipfile.ZipFile(cls.baseline) as archive:
            cls.classes={n:archive.read(n) for n in archive.namelist()}
        cls.helper=cls.helper_path.read_bytes()

    def test_recipe_preserves_input_dictionary(self):
        original=self.classes.copy()
        updates,_=patch.apply(self.classes,self.helper)
        self.assertEqual(self.classes,original)
        self.assertEqual(set(updates),{'MenuAnimal.class','SoccerMenuShowObjectModule.class','CXHumanPreview.class'})

    def test_all_unowned_method_bodies_remain_exact(self):
        updates,_=patch.apply(self.classes,self.helper)
        for name,owned in patch.EXPECTED.items():
            before=ClassFile(self.classes[name]);after=ClassFile(updates[name])
            for method in before.methods:
                label,desc=before.ref(method[1]),before.ref(method[2])
                if label+desc in owned:continue
                try:first=patch.body(before,label,desc)
                except StopIteration:continue
                self.assertEqual(first,patch.body(after,label,desc),(name,label,desc))

    def test_refuses_changed_owned_method(self):
        changed=self.classes.copy();c=ClassFile(changed['MenuAnimal.class'])
        c.edit('Reset',lambda data:b'\x00'+bytes(data),'()V')
        changed['MenuAnimal.class']=c.emit()
        with self.assertRaises(AssertionError):patch.apply(changed,self.helper)

    def test_refuses_already_patched_archive(self):
        changed=self.classes.copy();changed['CXHumanPreview.class']=self.helper
        with self.assertRaises(AssertionError):patch.apply(changed,self.helper)

    def test_refuses_incompatible_java_version(self):
        changed=bytearray(self.helper);struct.pack_into('>H',changed,6,49)
        with self.assertRaises(AssertionError):patch.apply(self.classes,bytes(changed))

    def test_external_fingerprints_match_embedded_guard(self):
        path=Path(patch.__file__).with_name('human_preview_fingerprints.json')
        self.assertEqual(json.loads(path.read_text(encoding='utf8')),patch.EXPECTED)

    def test_cli_preserves_archive_closure_and_registers_helper_once(self):
        temporary_root=(Path.cwd()/'build/human-preview-test-private').resolve()
        temporary_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='recipe-',dir=temporary_root) as private:
            root=Path(private).resolve()
            self.assertTrue(root.is_relative_to(temporary_root),'Cleanup target stays within the private test directory')
            index=root/'code_inf.pak'
            index.write_bytes(b'\r\n'.join(n.encode('utf8') for n in self.classes if n.endswith('.class'))+b'\r\n')
            output=root/'output'
            command=[sys.executable,'-m','src.patches.human_preview','--input',str(self.baseline),
                '--code-index',str(index),'--helper',str(self.helper_path),'--output',str(output)]
            subprocess.run(command,check=True,capture_output=True)
            updates,_=patch.apply(self.classes,self.helper)
            with zipfile.ZipFile(output/'code.pak') as archive:
                self.assertEqual(set(archive.namelist()),set(self.classes)|{'CXHumanPreview.class'})
                for name,data in self.classes.items():
                    self.assertEqual(archive.read(name),updates.get(name,data),name)
            self.assertEqual((output/'code_inf.pak').read_bytes().splitlines().count(b'CXHumanPreview.class'),1)
            manifest=json.loads((output/'manifest.json').read_text(encoding='utf8'))
            self.assertEqual(manifest['output_sha256'],hashlib.sha256((output/'code.pak').read_bytes()).hexdigest())
            # An existing destination must never be overwritten by a rerun.
            result=subprocess.run(command,capture_output=True)
            self.assertNotEqual(result.returncode,0)


if __name__=='__main__':unittest.main()
