# Changelog

Notable changes to eyewright. Versions are the distribution version.

## Unreleased

- `__version__` single-sourced from package metadata (no more drift).
- `serve` hardening: bearer token (constant-time), 1 MB body cap, generic errors,
  refusal to bind off-loopback without a token, optional TLS (`--cert`/`--key`).
- generative engine: robust first-object JSON extraction; canonical `yes`/`no`
  normalization (handles `true`/`false`, `1`/`0`).

## 0.3.1

- Scope the source distribution (exclude `bench/`): ~1.2 MB → 66 KB.

## 0.3.0

- Generative engine behind `ask` (`--engine generative` / `auto`), uncalibrated.
- Resilience: gate `retries` + `on_primary_unavailable`, `GET /health/deep`, and
  the service supervisor (`supervisor/`).

## 0.2.0

- One-call `ask`, HTTP `/v1/ask`, and the MCP adapter
  (`eyewright_gate` / `eyewright_ask`).

## 0.1.0

- Initial three-eye gate policy + validation bench (shipped as "oracle"; renamed
  to `eyewright` on 2026-10-09 — see `PROVENANCE.md`).
