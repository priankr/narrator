Run `python narrator.py voices` from the project root.

Parse the JSON output and present a filtered, readable summary:
- Show the `installed_model` version at the top.
- List voices where `available: true`, grouped by language prefix (e.g. `af_`/`am_` = American English, `bf_`/`bm_` = British English).
- Briefly note how many voices are `available: false` and which model version would unlock them (`v1.0`).
- If the user seems to want a non-English voice, suggest `python narrator.py setup --multilingual` and link to `wiki/configuration.md#multilingual-model`.
