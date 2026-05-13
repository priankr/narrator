# Narrator App — Claude Code Guide

Full agent instructions are in [wiki/agent-guidelines.md](wiki/agent-guidelines.md). Read that file first. This file adds Claude Code-specific conventions on top of it.

---

## Role

This repo is used in two ways:
- **Consumer:** invoke `narrator.py` to produce narrated audio from Markdown posts
- **Developer:** extend or maintain the Python codebase

Claude Code agents are almost always in **developer mode**. Default to that unless the task is purely about running the CLI to generate audio.

---

## Before Starting Any Task

1. Read [wiki/agent-guidelines.md — Part 2](wiki/agent-guidelines.md#part-2-developing-the-app-developer-agent) before touching any source file.
2. Use `TodoWrite` to break multi-step tasks into tracked items before starting. Mark each item complete immediately as you finish it — do not batch completions at the end.
3. Run `python narrator.py check` to confirm the environment is healthy before making pipeline changes that require testing.

---

## Custom Slash Commands

Project-specific commands are in `.claude/commands/`. Use them instead of constructing equivalent shell invocations manually.

| Command | Purpose |
|---|---|
| `/check` | Run environment check; surface issues with suggested fixes |
| `/status` | Show synthesis and output state for all posts, grouped by completion |
| `/voices` | List available voices filtered and grouped by installed model |
| `/generate` | Guided generate workflow: dry-run first, confirm before synthesizing |
| `/dry-run` | Validate a post's generate plan without running the pipeline |

The following CLI commands are pre-approved in `.claude/settings.json` and will not prompt for permission: `check`, `status`, `voices`, `config`, `setup --show-urls`, `generate … --dry-run`, `pytest -m "not slow"`.

---

## Tool Conventions

- Prefer `Read`, `Edit`, `Glob`, `Grep` over `Bash` for file operations.
- When editing a pipeline stage file, read the **full file** first. Stage contracts are tightly coupled and the context matters.
- Do not run `python narrator.py generate` on a real post without explicit user instruction — synthesis is slow (minutes) and writes files to disk.
- When you discover something non-obvious about the codebase — a quirk, a constraint, a design rationale — save it to memory so it is available in future sessions.

---

## Output Rules

- stdout is machine-readable JSON. Any new command you add must use `_ok()` or `_err()` — never `print()` plain text to stdout.
- Progress and hints go to stderr only.
- If you add a new CLI command or change a JSON response schema, update `wiki/agent-guidelines.md` section 1.3 to match.

---

## Committing

Do not commit unless explicitly asked. When asked:
- Stage only the relevant files by name — never `git add .`
- Write concise commit messages focused on the "why," not the "what"
- Include `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` as a trailer
