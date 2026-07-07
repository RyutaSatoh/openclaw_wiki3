# AGENTS.md

This repository is the clean restart after `openclaw_wiki2`.

## Intent

- Do not recreate the old `source page` layer here.
- Prefer common raw bundles over channel-specific intermediate pages.
- Keep Python dumb and inspectable.
- Let the OpenClaw LLM own:
  - family judgment
  - synthesis creation/update
  - visible prose

## Current workflow

1. `ingest-upstream` writes common raw bundles.
2. `prepare-openclaw` builds one family evidence pack and job manifest.
3. An OpenClaw turn writes decision/render JSON.
4. `apply-openclaw` writes markdown and updates indexes/logs.

## Constraints

- Prefer stdlib Python.
- Keep visible synthesis sections in Japanese.
- Avoid channel-specific logic unless it is strictly required for capture.
