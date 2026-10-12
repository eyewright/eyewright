# Security

## Reporting a vulnerability

Use GitHub's private reporting (Security → *Report a vulnerability*) on
`eyewright/eyewright`, or contact the maintainer directly. Please **do not** open
a public issue for a vulnerability.

## Trust model

eyewright runs **local, trusted configuration and code**. Two boundaries matter:

- **Gate config is code.** A config can name a `key_file` (read from disk, with
  `~`/env-var expansion) and a `url` (where the key is sent as a bearer token).
  Running an untrusted config can read a local file and POST its contents to an
  arbitrary host. Only run configs you trust. *(Hardening — restricting
  `key_file` to a directory and `url` to an allowlist — is tracked separately.)*
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
