"""Auditable bytecode recipe; call apply explicitly on isolated class bytes."""

import pathlib, struct, zipfile, json, hashlib, re

from tools.classfile import ClassFile as C, op, U2, U4, append

H = pathlib.Path(__file__).resolve().parent

ROWS = ["1 min (2x30 s)", "4 min (2x2 min)", "8 min (2x4 min)",
        "12 min (2x6 min)", "20 min (2x10 min)"]

TABLE = [2, 4, 6, 10, 1]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def body(c, name, desc):
    raw = c.code(name, desc)[1]
    return raw[8:8 + struct.unpack_from(">I", raw, 4)[0]]

def set_body(c, name, desc, code, stack=None, locals_=None):
    a = c.code(name, desc)
    old_stack, old_locals = struct.unpack_from(">HH", a[1])
    # Replaced bodies have no exception regions. Drop stale line/local offsets.
    old_n = struct.unpack_from(">I", a[1], 4)[0]
    assert a[1][8 + old_n:10 + old_n] == b"\0\0"
    a[1] = struct.pack(">HHI", stack or old_stack,
                       locals_ if locals_ is not None else old_locals, len(code))
    a[1] += code + b"\0\0\0\0"

class Asm:
    def __init__(self):
        self.b = bytearray()
        self.labels = {}
        self.fixups = []

    def put(self, data):
        self.b += data
        return self

    def label(self, name):
        self.labels[name] = len(self.b)
        return self

    def branch(self, opcode, label):
        self.fixups.append((len(self.b), label))
        self.b += bytes([opcode, 0, 0])
        return self

    def emit(self):
        for start, target in self.fixups:
            struct.pack_into(">h", self.b, start + 1, self.labels[target] - start)
        return bytes(self.b)

def mapping_code(to_saved):
    a = Asm()
    a.put(b"\x1a").branch(155, "invalid")  # iload_0; iflt
    a.put(b"\x1a\x08").branch(162, "invalid")  # >= 5
    a.put(b"\x1a" + (b"\x03" if to_saved else b"\x07"))
    a.branch(160, "ordinary")
    a.put((b"\x07" if to_saved else b"\x03") + b"\xac")
    a.label("ordinary").put(b"\x1a\x04" + (b"\x64" if to_saved else b"\x60") + b"\xac")
    a.label("invalid").put((b"\x04" if to_saved else b"\x05") + b"\xac")
    return a.emit()

def half_time_code(c):
    a = Asm()
    a.put(b"\x2a" + op(180, c.member("PlayerSave", "m_nMatchHalfTimeIndex", "I")) + b"\x3c")
    a.put(b"\x1b").branch(155, "fallback")
    a.put(b"\x1b\x08").branch(161, "valid")
    a.label("fallback").put(b"\x04\x3c")  # historical default index 1
    a.label("valid").put(b"\x1b\x07").branch(160, "old")
    a.put(b"\x10\x1e\xac")  # 30 seconds
    a.label("old").put(b"\x10\x3c" + op(178, c.member("CoreLogic", "_HALF_TIMES", "[I")) + b"\x1b\x2e\x68\xac")
    return a.emit()

def add_mapping(c, name, code):
    matches = [m for m in c.methods if c.ref(m[1]) == name]
    assert not matches
    c.methods.append([9, c.add(1, name), c.add(1, "(I)I"),
                      [[c.add(1, "Code"), U2(2) + U2(1) + U4(len(code)) + code + b"\0\0\0\0"]]])

def table_override(c):
    code = b"\x08\xbc\x0a"  # int[5]
    for i, value in enumerate(TABLE):
        value_code = bytes([3 + value]) if value <= 5 else bytes([16, value])
        code += b"\x59" + bytes([3 + i]) + value_code + b"\x4f"
    return code + op(179, c.member("CoreLogic", "_HALF_TIMES", "[I"))

def time_combo_code(c):
    code = b""
    combo = op(180, c.member("MenuOptionsMatch", "m_cHalfTime", "LUIComboBox;"))
    add = op(182, c.member("UIComboBox", "AddItem", "(Ljava/lang/String;Ljava/lang/Object;)I", 10))
    for label in ROWS:
        code += b"\x2a" + combo + op(19, c.string(label)) + b"\x01" + add + b"\x57"
    return code + b"\xb1"

def apply(classes):
    updates = {}
    c = C(classes["MenuOptionsMatch.class"])
    if any(c.ref(m[1]) == "CXTimeSavedIndex" for m in c.methods):
        # A partial/foreign patch must not be mistaken for a complete one.
        assert body(c, "CXTimeSavedIndex", "(I)I") == mapping_code(True)
        assert body(c, "CXTimeDisplayRow", "(I)I") == mapping_code(False)
        assert body(C(classes["PlayerSave.class"]), "GetHalfTime", "()I") == half_time_code(C(classes["PlayerSave.class"]))
        core = C(classes["CoreLogic.class"])
        assert body(core, "<clinit>", "()V").endswith(table_override(core) + b"\xb1")
        assert body(c, "FillTimeCombo", "()V") == time_combo_code(c)
        for name, helper in [("Show", "CXTimeDisplayRow"), ("OnOK", "CXTimeSavedIndex")]:
            assert body(c, name, "()V").count(op(184, c.member("MenuOptionsMatch", helper, "(I)I", 10))) == 1
        return {}
    expected = json.loads((H / "timing-source-methods.json").read_text())
    for filename, methods in expected.items():
        current = C(classes[filename])
        for key, digest in methods.items():
            name, desc = key.split("|", 1)
            assert sha(current.code(name, desc)[1]) == digest, (filename, key, "fresh audit required")

    # Append the fifth simulation entry only; all original initialization code
    # and original indices remain exactly as before.
    core = C(classes["CoreLogic.class"])
    old = body(core, "<clinit>", "()V")
    assert old[-1] == 177
    old_stack = struct.unpack_from(">H", core.code("<clinit>", "()V")[1])[0]
    set_body(core, "<clinit>", "()V", old[:-1] + table_override(core) + b"\xb1", stack=max(16, old_stack))
    updates["CoreLogic.class"] = core.emit()

    player = C(classes["PlayerSave.class"])
    set_body(player, "GetHalfTime", "()I", half_time_code(player), stack=3, locals_=2)
    updates["PlayerSave.class"] = player.emit()

    add_mapping(c, "CXTimeSavedIndex", mapping_code(True))
    add_mapping(c, "CXTimeDisplayRow", mapping_code(False))
    set_body(c, "FillTimeCombo", "()V", time_combo_code(c), stack=3)
    show = body(c, "Show", "()V")
    assert show[79] == 180 and show[82] == 182
    set_body(c, "Show", "()V", show[:82] + op(184, c.member("MenuOptionsMatch", "CXTimeDisplayRow", "(I)I", 10)) + show[82:])
    ok = body(c, "OnOK", "()V")
    assert ok[119] == 182 and ok[122] == 181
    # The sole conditional branch in this method ends at112, before insertion.
    assert ok[81:84] == b"\x99\x00\x1f"
    set_body(c, "OnOK", "()V", ok[:122] + op(184, c.member("MenuOptionsMatch", "CXTimeSavedIndex", "(I)I", 10)) + ok[122:])
    updates["MenuOptionsMatch.class"] = c.emit()
    return updates

def apply_text(data):
    old = 'String("MenuOptionsMatchLabelTime", "Czas trwania połowy")'.encode("cp1250")
    new = 'String("MenuOptionsMatchLabelTime", "Czas meczu")'.encode("cp1250")
    if new in data:
        return data
    assert data.count(old) == 1
    return data.replace(old, new)
