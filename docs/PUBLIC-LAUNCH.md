# Public launch checklist

> **Internal runbook** — not part of the public-facing docs (those are the repo
> `README.md`, `docs/*` policy docs, and `LICENSE`/`CONTRIBUTING.md`/`SECURITY.md`).

Gate to flip `eyewright/eyewright` from **private → public**. Repo is private as of
2026-10-12 by decision; nothing below is done unless checked. Work top to bottom.

## 0. Decide
- [x] **License:** **Apache-2.0 + `NOTICE` + DCO** (decided 2026-10-12). Wired:
      `LICENSE`, `NOTICE`, `DCO`, `CONTRIBUTING.md`, `AUTHORS`, `PROVENANCE.md`,
      and the `pyproject.toml` metadata.
- [x] **What ships:** `bench/` trimmed — the raw `responses-*.jsonl` are removed
      (29 files backed up to `%USERPROFILE%\ai-cache\eyewright-bench`, gitignored,
      regenerable); scripts + cases + `*.md` stay. `bench/` ≈ 6.8 MB (was 19.5 MB).
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
- [x] history scanned (all 14 commits) — no keys/tokens; `.env`, `*.key`,
      `*api-key*`, `dist/`, `.venv/`, `*.log`, `*.pid` were never tracked
- [x] personal paths scrubbed (`%USERPROFILE%` / `%OneDrive%` / env vars;
      `key_file` + supervisor `cwd` now expand env vars). Only the `kcpatt27`
      handle remains (attribution).
- [x] `publish/RESERVE.md` / `docs/` / `bench/` reviewed — synthetic data only
      (fake `example.com` emails, RFC-5737 IPs); no real PII
- [x] `supervisor/logs/` + `*.pid` are gitignored

## 3. Docs
- [x] README: install/quickstart, egress, security, license sections (PR #19, #10)
- [ ] 90-second demo (LAUNCH.md §5)
- [x] internal vs public docs: runbooks labelled internal + `docs/README.md` index
- [x] 5 `good first issue`s filed (#1, #2, #8, #9, #10); #1/#2/#10 already fixed

### Bug / issue audit (2026-10-12)

Ten issues filed from a full read of the source (`eyewright/eyewright#1`–`#10`):

- **bugs:** #1 `__version__` drift · #2 generative `true`/`false` unnormalized ·
  #3 `_extract_json` greedy · #4 `engine=auto` fallback scope · #5 `retries`
  off-by-one · #6 hardcoded 1800 s timeouts · #7 `serve` request hardening
- **enhancements:** #8 MCP `levels` · #9 CI (tests + build)
- **docs:** #10 README quickstart + license section

### Security pass (2026-10-12)

New `security` label; issues #12–#17:
- #12 TLS / plaintext transport off-loopback
- #13 config trust boundary (`key_file` + `url` can exfiltrate local files)
- #14 document cloud-eye egress (`state` leaves the box)
- #15 pin `mcp` + dependency auditing
- #16 serve concurrency cap / rate limit
- #17 local-exec trust (svcwatch / `--start-services`)

**Merged:** PR #11 (#1, #7) · PR #18 (#2, #3, #12) · PR #19 (#10, #14, #17).

**Open:** #4 `engine=auto` fallback · #5 `retries` semantics · #6 timeouts ·
#8 MCP `levels` · #9 CI · #13 config `key_file`/`url` hardening · #15 pin `mcp` ·
#16 rate limit.

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
`%OneDrive%/Documents/Default Project/oracle-mcp/LAUNCH.md`.
