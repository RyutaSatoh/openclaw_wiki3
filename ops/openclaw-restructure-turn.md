Use the OpenClaw LLM to run one `wiki3` restructure review batch.

Model:

- `openai/gpt-5.4-mini`

Workflow:

1. Build the batch manifest with:
   `python3 scripts/wiki3.py restructure-batch`
2. For each family:
   - or rebuild a single-family job with
     `python3 scripts/wiki3.py restructure-prepare --family <family>`
   - read the emitted job manifest
   - read the evidence pack, restructure prompt, and restructure schema
   - write one restructure proposal JSON with `apply_patch`
   - run `python3 scripts/wiki3.py restructure-apply --job <job-path>`
3. After all families finish:
   - if git changed, commit once and push once

Rules:

- Do not rewrite synthesis pages directly in this phase.
- This phase only proposes structural changes such as split, split+link, link-only, or merge review.
- Keep the proposal practical and grounded in the bundles and the current page.
- Write all explanatory text in Japanese.
