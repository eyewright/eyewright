# Contributing

Thanks for helping eyewright.

## Sign your commits (DCO)

Every commit must be signed off under the [Developer Certificate of Origin](DCO)
1.1 — a lightweight statement that you wrote the code, or have the right to
submit it. Contributors **keep their own copyright**; this is not a CLA.

Sign off automatically:

```
git commit -s
```

which appends a trailer such as:

```
Signed-off-by: Your Name <you@example.com>
```

Use a real name and a valid email. Commits without a sign-off can't be merged.

## Dev setup

```
uv sync                  # venv + default `runtime` group (mcp, pystray, pillow)
uv run eyewright --help
uv run python tests/mcp_smoke.py
```

The gate policy in `eyewright/gate.py` is the single source of truth; the
validation bench lives in `bench/` and docs in `docs/`.

## Pull requests

- Keep changes focused; tests / the smoke test pass.
- Note significant changes in the files you edit (Apache-2.0 §4b).
- The local decision services (`laya-serve`, Ollama) are optional for
  packaging/docs work; the smoke test needs them for a live gate call.
