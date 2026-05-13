Validate a generate plan without running the pipeline.

Arguments: $ARGUMENTS (post path and any flags, e.g. `posts/my-essay.md --voice am_adam --format m4a`)

Run `python narrator.py generate $ARGUMENTS --dry-run` from the project root.

If $ARGUMENTS is empty, ask the user which post and options to validate before running.

Parse and present the resolved plan:
- `post_name`, `voice`, `speed`, `format`, `output_path`
- Whether the run `would_skip` (output already exists and `--force` was not passed)
- `skip_intro`, `skip_outro`, `force` flag states

If the dry run exits with code 1, show the `message` field and explain which flag caused the validation failure.
