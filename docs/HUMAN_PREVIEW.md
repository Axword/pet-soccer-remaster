# Gothic and Witcher menu previews

This contribution contains original mod source and a guarded transformation
recipe. It distributes no original game classes, decompiled game implementations,
game archives, character assets or native renderer. Build against your own local
game and the reviewed beta2 mod code archive.

The helper limits the 14 human menu models to their existing authored idle/look
clips. It resets reused preview animation state, preserves delayed selection
through hide/show, cancels obsolete callbacks and keeps Cup/Instant positioning.
On arrival, it faces only the current human menu actor toward the current camera.
Actual native captures establish opposite front axes: Gothic is local -Z and
Witcher is local +Z. The exact filename guard precedes normalized-basename family
selection. Stock/Minecraft actors and gameplay models are unaffected.

This helper does not change materials, culling or rendering flags. Controlled
native comparison excluded culling as the cause of the Witcher gaps. A separate
asset investigation found holes in an earlier mesh simplification; repairing
that geometry is independent of these menu animation and lifecycle changes.

Compile the original helper using the repository's `tools/compile_java.py`, your
external Java 1.3 runtime and an external compatible Eclipse compiler. Then run
from the repository root:

```text
python -m src.patches.human_preview --input path/to/reviewed-beta2-code.pak --code-index path/to/code_inf.pak --helper build/java/CXHumanPreview.class --output build/human-preview
```

The output directory must be new. Installers need both emitted `code.pak` and
`code_inf.pak`. Keep them local or use the repository's mod-only delta packaging;
the recipe does not grant redistribution rights to the underlying game code.
Every transformed original method is checked against a published SHA256
fingerprint. Unknown or already patched inputs are refused. Other archive
entries and unowned method bodies remain exact.

Optional original Python tests read external local inputs and create temporary
outputs; no original compiled fixture or game type is included in the source:

```text
PET_SOCCER_CODE_PAK=path/to/reviewed-beta2-code.pak
PET_SOCCER_PREVIEW_HELPER=build/java/CXHumanPreview.class
python -m unittest discover -s tests -p test_human_preview.py -v
```

Set the two variables using your shell's environment syntax. These recipe tests
check archive closure, guards, non-mutating patch composition and unowned-method
preservation. They do not run the native engine. Private developer JVM checks
cover 1164 assertions across all 14 humans, including both family signs,
normal/Cup/Instant, stale actor/cache handling, repeated arrivals and path case
and slash variants.
Those private checks use modified local native API
boundaries; their derived original fixture classes are deliberately excluded.
Real screenshots and engine logs remain the separate visual acceptance gate.

Source provenance: `CXHumanPreview.java`, this transformation recipe, its hash
metadata and the Python tests were authored for this mod. Referenced game API
names describe the external interface. Apply the repository's existing license
to this original contribution; no license is asserted over the underlying game,
Gothic/Witcher assets or third-party tooling.
