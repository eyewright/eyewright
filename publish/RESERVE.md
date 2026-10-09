# Reserve `eyewright` — PyPI + npm + GitHub

One-time runbook. Reserving is **irreversible** (PyPI/npm names are permanent
once published) and **free**. Decision + rationale: **ADR-0005**
(`local-ai-system/docs/decisions/ADR-0005-public-name-eyewright.md`).

Preflight (all three were 404 = free, 2026-10-09; re-check before claiming):

```powershell
(Invoke-WebRequest -Uri "https://pypi.org/pypi/eyewright/json" -SkipHttpErrorCheck).StatusCode      # want 404
(Invoke-WebRequest -Uri "https://registry.npmjs.org/eyewright/latest" -SkipHttpErrorCheck).StatusCode # want 404
(Invoke-WebRequest -Uri "https://api.github.com/orgs/eyewright" -SkipHttpErrorCheck).StatusCode        # want 404
```

---

## 1. PyPI

The real distribution already builds: `dist/eyewright-0.3.0.tar.gz` +
`eyewright-0.3.0-py3-none-any.whl` (`uv build`). Publishing it reserves the name
**and** ships the actual tool.

1. Create / confirm an account at <https://pypi.org/account/register/> and verify
   email. PyPI now **requires 2FA** to upload.
2. Create an API token: <https://pypi.org/manage/account/token/> → **Add API
   token** → scope *Entire account* (a project-scoped token can't be made until
   the project exists).
3. Publish from the repo root:

   ```powershell
   cd C:\Users\kcpat\projects\oracle
   uv build                                   # refresh dist/ if sources changed
   $env:UV_PUBLISH_TOKEN = "pypi-<paste-token>"
   uv publish
   ```

   (Or one-shot: `uv publish --token pypi-<paste-token>`.)
4. Verify (expect **200**):

   ```powershell
   (Invoke-WebRequest -Uri "https://pypi.org/pypi/eyewright/json" -SkipHttpErrorCheck).StatusCode
   ```

> Prefer a **placeholder** (hold the real 0.3.0 until launch)? Say so — minimal
> alternative: a 0.0.1 `pyproject.toml` under `publish/pypi/`. Not scaffolded by
> default because the real dist is ready and lighter to maintain.

---

## 2. npm

Placeholder package is scaffolded at `publish/npm/` (name reservation only).
`npm` is already logged in as `kcpatt27`.

```powershell
cd C:\Users\kcpat\projects\oracle\publish\npm
npm whoami                        # expect: kcpatt27
npm publish --access public       # add --otp=<6-digit> if 2FA prompts
```

Verify (expect **200**):

```powershell
(Invoke-WebRequest -Uri "https://registry.npmjs.org/eyewright/latest" -SkipHttpErrorCheck).StatusCode
```

> The scaffold declares `"license": "Apache-2.0"` and homepage/repo
> `github.com/eyewright/eyewright` — flip these if you choose differently.

---

## 3. GitHub org + repo

Creating the **org** is what reserves `eyewright` on GitHub (a personal repo
under `kcpatt27/eyewright` would **not** block someone else taking the org). Org
creation is web-only:

1. <https://github.com/settings/organizations> → **New organization** → **Free** →
   name **`eyewright`**.
2. Create the repo (empty, private until launch):

   ```powershell
   gh repo create eyewright/eyewright --private `
     --description "eyewright - local decision core (three-eye gate + one-call typed decisions)"
   ```

3. Optional, before the public launch: rename the working directory and push.

   ```powershell
   # later, deliberately (breaks venv + harness paths until re-synced):
   Rename-Item C:\Users\kcpat\projects\oracle eyewright
   cd C:\Users\kcpat\projects\eyewright
   git remote add origin https://github.com/eyewright/eyewright.git
   uv sync --extra mcp
   ```

---

## 4. After claiming

Record the date in ADR-0005 (`Reservation date: __`) and flip the registry table's
`reservation` column from `pending` to `reserved`.

**Report back:** the date is the only missing field in the ADR.
