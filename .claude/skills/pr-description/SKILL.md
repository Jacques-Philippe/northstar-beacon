---
name: pr-description
description: Generates a PR title and description from the changes on the current branch vs. master. Writes to mr-meta.md.
---

Generates a pull request title and description by analysing the diff between the current branch and a base branch.

**Arguments** (optional, passed as `$ARGUMENTS`):

- `--base-branch <branch>` — Compare against this branch (default: `master`)
- `--output-file <path>` — Where to write the output (default: `./mr-meta.md`)

## Execution Steps

1. **Parse arguments** from `$ARGUMENTS` — extract `--base-branch` and `--output-file` if provided; fall back to defaults
2. **Gather context** — run these in parallel:
   - `git rev-parse --abbrev-ref HEAD` — current branch name
   - `git diff --name-only <base_branch>...HEAD` — changed files
   - `git log <base_branch>...HEAD --oneline` — commit history
3. **Read the diffs** — for each changed file run `git diff <base_branch> -- <file>` and read the full file if needed for context. Skip binary files and `.meta` files.
4. **Synthesise** — from the commits and diffs, identify:
   - The primary goal of the branch (one sentence)
   - The key changes grouped by theme (new features, fixes, refactors, tests, docs)
   - Any breaking changes to public API
5. **Output** the PR title and description to the specified output file in markdown format, following the template below.

## Output Format

Print the following to the output file:

```
## PR Title
<title — imperative mood, under 60 chars, e.g. "Add drag and rotation to puzzle pieces">

## PR Description

### What
<2–6 bullet points describing what changed and why>

### How
<2–6 bullet points on the implementation approach — key design decisions worth calling out>

### Testing
<1–6 bullet points: what tests were added and what they cover>

### Notes
<Optional: breaking changes, known limitations, follow-up work>
```

The squash commit message section follows immediately after the PR description:

```
## Squash Commit Message
<subject line — same as PR title>

- <key change>
- <key change>
- <key change>
```

## Guidelines

- Title: imperative mood ("Add", "Fix", "Remove"), no trailing period, under 60 characters
- Be specific — reference actual class/file names where helpful
- "What" focuses on the user-facing or developer-facing outcome, not the mechanics
- "How" focuses on design decisions and architecture, not line-by-line changes
- Omit "Notes" section entirely if there is nothing meaningful to say
- Do not include a "🤖 Generated with Claude" footer
- Squash commit subject: identical to the PR title (already imperative, under 60 chars)
- Squash commit body: unordered list with `-`, 3–6 items, one idea per bullet, no section headers — just the key facts a future `git log` reader needs
