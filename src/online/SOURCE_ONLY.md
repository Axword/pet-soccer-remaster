These are owned source files, not a game installation or runtime workspace.

Use `tools/prepare_online_workspace.py`, `tools/build_online_runtime.py`,
`tools/build_online_launcher.py` and `tools/test_online.py` from the repository.
They stage generated binaries, databases, logs and tests under ignored `build/`.
The shipped runtime is obtained from a pinned official archive or verified
`package/payload/online/runtime`; its binaries are not duplicated here.

See [ONLINE_BUILD.md](../../docs/ONLINE_BUILD.md).
