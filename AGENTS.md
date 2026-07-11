# AGENTS.md

This repository is the clean restart after `openclaw_wiki2`.

## Intent

- Follow a bundle-first `Ingest / Query / Lint` shape.
- Do not recreate the old `source page` layer here.
- Prefer common raw bundles over channel-specific intermediate pages.
- Keep Python dumb and inspectable.
- Let the OpenClaw LLM own:
  - family judgment
  - synthesis creation/update
  - visible prose

## Current workflow

1. `ingest` writes common raw bundles.
2. `query-prepare` or `query-batch` builds evidence packs and job manifests.
3. An OpenClaw turn writes decision/render JSON.
4. `query-apply` writes markdown and updates indexes/logs.
5. `lint` reports freshness, coverage gaps, and broad-page signals.
6. `restructure-*` builds and records structure proposals such as split/link candidates.

## Constraints

- Prefer stdlib Python.
- Keep visible synthesis sections in Japanese.
- Avoid channel-specific logic unless it is strictly required for capture.
- When adding new domains like `children` or `chat`, prefer new families or
  family classes rather than new Python meaning-making layers.
