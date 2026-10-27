# Security

## Reporting a vulnerability

Use GitHub's private reporting (Security → *Report a vulnerability*) on
`eyewright/eyewright`, or contact the maintainer directly. Please **do not** open
a public issue for a vulnerability.

## Trust model

eyewright runs **local, trusted configuration and code**. Two boundaries matter:

- **Gate config is code.** A config can name a `key_file` (read from disk, with
  `~`/env-var expansion) and a `url` (where the key is sent as a bearer token).
  Only run configs you trust. Guardrails are enforced in `gate.py`:
  - **URL allowlist** — `systemone-http` eyes may only reach loopback
    (`127.0.0.1` / `::1` / `localhost`); `openrouter-decisions` eyes may only reach
    `openrouter.ai`. A remote host is refused unless the entry sets
    `"allow_remote": true`.
  - **Sensitive key files rejected** — `key_file` paths under `~/.ssh`, `~/.aws`,
    `~/.gnupg`, `~/.config/gcloud`, `~/.azure`, `~/.kube`, or named like
    `id_rsa`/`credentials`/`.env`/`.npmrc`/… are refused.
- **Local exec.** `supervisor/svcwatch.py` runs commands from
  `supervisor/services.json`, and `eyewright gate --start-services` runs the
  supervisor as `sys.executable`. Both execute local scripts; run from a repo you
  trust.

## Serving

`eyewright serve` is **loopback-only by default**. Binding off-loopback
(`--host 0.0.0.0`) **requires** a bearer token (`--token` / `$EYEWRIGHT_TOKEN`)
and the server sends `401` without it. Use `--cert`/`--key` for HTTPS, or a
TLS terminator / SSH-VPN tunnel. The token authenticates callers; it is **not**
encryption. Request bodies are capped (default 1 MB).

## Egress

The default gate is fully local. Adding an `openrouter-decisions` eye sends
`state`/`question` to OpenRouter; `"zdr": true` is request-level routing, not a
guarantee. See the README "Egress & privacy" section.
