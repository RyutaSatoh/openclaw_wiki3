Use the OpenClaw LLM to run one `wiki3` synthesis batch.

Model:

- `openai/gpt-5.4-mini`

Workflow:

1. Read the batch prompt to know which families to process.
   Optionally use `python3 scripts/wiki3.py prepare-batch` when the prompt asks
   for one manifest covering multiple families.
2. For each family:
   - run `python3 scripts/wiki3.py prepare-openclaw --family <family>`
   - read the emitted job manifest
   - read the evidence pack, decide prompt, and decide schema
   - write decision JSON with `apply_patch`
   - if action is not `hold_source_only`, read render prompt and render schema
   - write render JSON with `apply_patch`
   - run `python3 scripts/wiki3.py apply-openclaw --job <job-path>`
3. After all families finish:
   - if git changed, commit once and push once

Rules:

- Do not call external LLM APIs from Python.
- Keep JSON outputs schema-valid.
- Keep visible markdown human-readable and source-grounded.
