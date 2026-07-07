# BUNDLE_SCHEMA

`raw/bundles/` stores channel-agnostic raw bundles.

Python should not decide durable meaning here.
It should only preserve enough structure for later LLM retrieval.

## Required fields

- `id`
- `ts`
- `origin`
- `title`
- `summary`
- `content`
- `topics`
- `artifacts`
- `provenance`

## Origin types

- `promoted_digest`
- `legacy_source_page`
- future examples:
  - `discord_message`
  - `cron_digest`
  - `web_item`
  - `session_turn`

## Design rule

Bundles should preserve raw evidence and light metadata.
They should not compress a topic down to one Python-authored interpretation.
