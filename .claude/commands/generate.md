Guided narration generation workflow.

Arguments: $ARGUMENTS (post path and any flags, e.g. `posts/my-essay.md --voice af_bella`)

Steps:
1. If no post path is in $ARGUMENTS, run `python narrator.py status` to show available posts and ask the user which one to generate.
2. Run `python narrator.py generate $ARGUMENTS --dry-run` to validate inputs and show the resolved plan.
3. Present the plan to the user: `post_name`, `voice`, `speed`, `format`, `output_path`, whether it `would_skip`, and note that `--cache-segments` can be added to write segment files to disk and enable resume-on-failure for this run.
4. If `would_skip` is `true`, ask whether to add `--force`.
5. Ask for explicit confirmation before running the full pipeline. Do not proceed without it — synthesis takes several minutes and writes to disk.
6. On confirmation, run `python narrator.py generate $ARGUMENTS`.
7. On success, report `output_path` and `duration_sec`. On error, surface the `message` field verbatim.
