Use the OpenClaw LLM to run one `wiki3` query batch.

Model:

- `openai/gpt-5.4-mini`

Workflow:

1. Build the batch manifest with:
   `python3 scripts/wiki3.py query-batch`
2. For each family:
   - or rebuild a single-family job with
     `python3 scripts/wiki3.py query-prepare --family <family>`
   - read the emitted job manifest
   - read the evidence pack, decide prompt, and decide schema
   - write decision JSON with `apply_patch`
   - if action is not `hold_source_only`, read render prompt and render schema
   - write render JSON with `apply_patch`
   - run `python3 scripts/wiki3.py query-apply --job <job-path>`
3. After all families finish:
   - if git changed, commit once and push once

Rules:

- Do not call external LLM APIs from Python.
- Keep JSON outputs schema-valid.
- Keep visible markdown human-readable and source-grounded.
- Treat this as the `Query` phase of the wiki. `Ingest` and `Lint` are separate.
