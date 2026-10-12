# Public launch checklist

Gate to flip `eyewright/eyewright` from **private → public**. Repo is private as of
2026-10-12 by decision; nothing below is done unless checked. Work top to bottom.

## 0. Decide
- [x] **License:** **Apache-2.0 + `NOTICE` + DCO** (decided 2026-10-12). Wired:
      `LICENSE`, `NOTICE`, `DCO`, `CONTRIBUTING.md`, `AUTHORS`, `PROVENANCE.md`,
      and the `pyproject.toml` metadata.
- [ ] **What ships:** keep `bench/*.jsonl` research data in the public repo, or
      strip to code + docs? (Already excluded from the sdist; still in git.)
- [ ] **Family shape:** is `eyewright` only the gate, or the house name? Affects the
      README framing and the GitHub org description.

## 1. Legal / provenance
- [x] `LICENSE` (Apache-2.0) + `NOTICE` at repo root
- [x] `pyproject.toml`: `license = "Apache-2.0"`, `license-files`, `[project.urls]`,
      classifiers (build verified: PEP 639 `License-Expression`)
- [x] `AUTHORS` + `PROVENANCE.md` (model-lab decision-bench 2026-10-06 →
      `oracle` repo 2026-10-08 → `eyewright` rename 2026-10-09)
- [x] `DCO` + `CONTRIBUTING.md` (commits require `git commit -s` sign-off)
- [ ] `publish/npm/package.json`: already `Apache-2.0` — confirm at publish time
- [ ] PyPI metadata carries no license (0.3.1 predates this): ship the license on
      the next version bump (`uv version --bump patch` → publish)

## 2. Secret / sensitive scan (full git history, not just HEAD)
- [ ] scan history for keys/tokens (`pypi-AgEI`, `npm_`, `sk-`, `gho_`, `-----BEGIN`)
- [ ] confirm `.env`, `*.key`, `*api-key*`, `dist/`, `.venv/`, `*.log`, `*.pid` were
      never tracked
- [ ] review `publish/RESERVE.md`, `docs/`, `bench/` for anything private
- [ ] `supervisor/logs/` + `*.pid` untracked (verify)

## 3. Docs
- [ ] README outcome-first: one-liner, bench card, install line, repo URL
- [ ] 90-second demo (LAUNCH.md §5)
- [ ] split internal vs public docs; remove or clearly label internal notes
- [ ] 5 `good first issue`s

## 4. Package metadata
- [ ] PyPI: classifiers, keywords, `[project.urls]` (Homepage / Repository / Issues)
- [ ] clean-env check: `pip install eyewright` → `python -c "import eyewright"`
- [ ] npm `eyewright@0.0.1` page links resolve

## 5. Flip
- [ ] `gh repo edit eyewright/eyewright --visibility public --accept-visibility-change-consequences`
- [ ] repo description + topics (`eyewright`, `mcp`, `decision-gate`, `local-first`)
- [ ] fresh `git clone` of the public URL works
- [ ] tag the launch version and push the tag

## 6. Launch
- [ ] Show HN / r/LocalLLaMA / r/mcp / X thread (LAUNCH.md §5–7)
- [ ] MCP directories (awesome-mcp-servers, Smithery, Glama, PulseMCP, mcp.so)
- [ ] reply within the hour for 48h

## 7. Post
- [ ] triage issues; first external bug → fix + credit
- [ ] day-30 metrics decision (LAUNCH.md §9)

**Pointers:** `publish/RESERVE.md` (name reservations — done) ·
`C:\Users\kcpat\OneDrive\Documents\Default Project\oracle-mcp\LAUNCH.md`.
