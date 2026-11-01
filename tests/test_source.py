"""Source-only tests; no game, original assets or network are required."""
from pathlib import Path
import ast, importlib, struct, sys, unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.classfile import ClassFile, U2, U4
from src.patches.console_guard import instructions

def tiny_class():
    utf=lambda text:b'\x01'+U2(len(text))+text.encode('ascii')
    pool=[utf('Sample'),b'\x07\x00\x01',utf('java/lang/Object'),b'\x07\x00\x03',
          utf('Code'),utf('answer'),utf('()I')]
    code=U2(1)+U2(0)+U4(3)+b'\x10\x2a\xac'+U2(0)+U2(0)
    method=U2(9)+U2(6)+U2(7)+U2(1)+U2(5)+U4(len(code))+code
    return b'\xca\xfe\xba\xbe'+U2(0)+U2(47)+U2(8)+b''.join(pool)+U2(0x21)+U2(2)+U2(4)+U2(0)+U2(0)+U2(1)+method+U2(0)

class SourceTests(unittest.TestCase):
    def test_class_roundtrip_preserves_exact_bytes(self):
        data=tiny_class();self.assertEqual(ClassFile(data).emit(),data)

    def test_constant_pool_add_is_deduplicated(self):
        c=ClassFile(tiny_class());first=c.string('new-label')
        self.assertEqual(c.string('new-label'),first)
        self.assertEqual(ClassFile(c.emit()).ref(first),'new-label')

    def test_decoder_does_not_match_opcode_inside_operand(self):
        code=b'\x11\xb8\x05\xb8\x00\x01\xb1'
        self.assertEqual(list(instructions(code)),[(0,17),(3,184),(6,177)])

    def test_decoder_tracks_switch_alignment(self):
        code=b'\x00\xaa\0\0'+struct.pack('>iiiii',0,0,1,0,0)+b'\xb1'
        self.assertEqual(list(instructions(code)),[(0,0),(1,170),(24,177)])

    def test_recipe_modules_import_without_external_inputs(self):
        for file in (ROOT/'src/patches').glob('*.py'):
            if file.stem!='__init__':self.assertTrue(importlib.import_module('src.patches.'+file.stem))

    def test_all_published_python_is_syntactically_valid(self):
        folders=['tools','src','tests','authoring']
        for name in folders:
            for file in (ROOT/name).rglob('*.py'):
                ast.parse(file.read_text(encoding='utf8'),filename=str(file))

    def test_native_local_include_closure(self):
        import re
        for file in (ROOT/'src/native').rglob('*'):
            if file.suffix not in ['.cpp','.h']:continue
            for relative in re.findall(r'^#include "([^"]+)"',file.read_text(encoding='utf8'),re.M):
                target=(file.parent/relative).resolve()
                self.assertTrue(target.is_relative_to((ROOT/'src/native').resolve()))
                self.assertTrue(target.is_file(),str(target))

    def test_authoring_recipes_require_isolated_workspace(self):
        for file in (ROOT/'authoring/recipes').rglob('*.py'):
            text=file.read_text(encoding='utf8')
            self.assertIn('PETSOCCER_AUTHORING_WORKSPACE',text)
            self.assertIn('is_relative_to',text)

if __name__=='__main__':unittest.main()
