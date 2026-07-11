# openclaw_wiki3

Bundle-first LLM wiki for OpenClaw.

`wiki3` is the clean restart after earlier source-page-heavy prototypes.
The goal is to follow the Karpathy-style `Ingest / Query / Lint` shape while
fitting OpenClaw's actual environment: cron turns, mixed channels, and
Japanese human-facing syntheses.

## Core ideas

1. `Ingest` stores thin raw bundles
2. `Query` lets the OpenClaw LLM decide `hold / update / create`
3. `Query` also lets the OpenClaw LLM render the visible synthesis in Japanese
4. `Lint` checks freshness, section completeness, and bundle coverage gaps
5. Python stays narrow: capture, retrieval, file write, and bookkeeping

## Layout

- `raw/bundles/`: channel-agnostic raw bundles
- `raw/runs/`: query manifests, evidence packs, lint reports, LLM outputs
- `wiki/`: human-facing syntheses and index/log
- `schema/`: bundle, prompt, and JSON schema docs
- `config/wiki3.json`: family definitions, upstream inputs, lint settings
- `scripts/wiki3.py`: CLI for `ingest`, `query-*`, and `lint`
- `ops/openclaw-batch-turn.md`: unified OpenClaw batch runbook
- `ops/openclaw-restructure-turn.md`: OpenClaw restructure-review runbook

## Current families

- `china-tech-news`
- `tailored-tech-news`

## CLI

```bash
python3 scripts/wiki3.py ingest
python3 scripts/wiki3.py query-prepare --family china-tech-news
python3 scripts/wiki3.py query-batch
python3 scripts/wiki3.py query-apply --job raw/runs/<job>.json
python3 scripts/wiki3.py restructure-prepare --family china-tech-news
python3 scripts/wiki3.py restructure-batch
python3 scripts/wiki3.py restructure-apply --job raw/runs/<job>.json
python3 scripts/wiki3.py lint
```

Compatibility aliases from the first `wiki3` sketch still exist:
`ingest-upstream`, `prepare-openclaw`, `prepare-batch`, `apply-openclaw`.

## Current scope

- Ingest upstream news/cache artifacts into common raw bundles
- Build family evidence packs from bundles
- Run OpenClaw query jobs in batch
- Render Japanese visible syntheses
- Emit lint reports for quality gaps
- Emit restructure review jobs when fixed pages grow too broad

## Deliberate non-goals

- Python-authored source pages
- Rich routing heuristics baked into Python
- Channel-specific durable interpretation during ingest
- Full migration from older repos before the model is proven
