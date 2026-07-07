# openclaw_wiki3

Bundle-first wiki prototype for OpenClaw.

This repository intentionally avoids Python-authored source pages.
The design goal is:

1. Capture channel-agnostic raw bundles
2. Build evidence packs from bundles, not from heuristic source summaries
3. Let the OpenClaw LLM decide `hold / update / create`
4. Let the OpenClaw LLM render human-readable Japanese syntheses
5. Keep Python narrow: ingest, retrieval, file write, bookkeeping

## Layout

- `raw/bundles/`: append-friendly raw bundle files
- `raw/runs/`: evidence packs and LLM outputs
- `wiki/`: human-facing syntheses
- `schema/`: bundle and response schemas
- `config/wiki3.json`: family definitions and upstream inputs
- `scripts/wiki3.py`: minimal CLI
- `ops/openclaw-batch-turn.md`: unified cron runbook

## Current families

- `china-tech-news`
- `tailored-tech-news`

## Current scope

- Ingest upstream news/cache artifacts into common raw bundles
- Build family evidence packs from bundles
- Batch-oriented OpenClaw handoff
- Japanese visible syntheses

## Non-goals for first cut

- Python-authored source pages
- Rich ranking heuristics
- Cross-family graph reasoning
- Full migration from older repos
