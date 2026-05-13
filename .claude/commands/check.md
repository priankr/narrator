Run `python narrator.py check` from the project root.

Parse the JSON output:
- If `status` is `"ok"`: confirm the environment is ready. Show the `installed_model` version and the default voice and format from the returned config.
- If `status` is `"error"`: surface each item in the `issues[]` array to the user. For each issue, suggest the appropriate fix using the error recovery table in `wiki/agent-guidelines.md` section 1.5. Do not proceed with any other task until all issues are resolved.
