Run `python narrator.py status` from the project root.

Parse the JSON output and present the posts list in a readable format:
- Group posts into three states: **Done** (synthesis cached + output file exists), **Synthesized** (cached but no output file), **Not started** (no manifest).
- For each post show: name, synthesis progress (`segments_done`/`total_paragraphs`), voice and speed used, and any output files found.
- If `posts[]` is empty, note that no `.md` files were found in `posts/`.
