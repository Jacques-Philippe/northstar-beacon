---
name: create-pr
description: Generates a PR title and description from the changes on the current branch vs. master, opens (or updates) a pull request on the origin GitHub remote, and squash-merges it with the generated squash commit message.
---

Generates a pull request title and description by analysing the diff between the current
branch and a base branch, opens the PR on GitHub against the `origin` remote (or updates the
existing open PR for the branch), then **squash-merges it** using the generated squash
commit message and deletes the branch. Pass `--no-merge` to stop after opening the PR.

**Arguments** (optional, passed as `$ARGUMENTS`):

- `--base-branch <branch>` — Compare against / target this branch (default: `master`)
- `--draft` — Open the PR as a draft (implies `--no-merge` — drafts can't be merged)
- `--no-merge` — Open / update the PR but do not merge it
- `--dry-run` — Do everything except create/update/merge the PR; print the title, body and
  squash message instead

## Execution Steps

1. **Parse arguments** from `$ARGUMENTS` — extract `--base-branch`, `--draft`, `--no-merge`,
   `--dry-run`; fall back to defaults. `--draft` implies `--no-merge`.
2. **Preflight** — run in parallel and stop with a clear message if any fails:
   - `gh auth status` — must be authenticated. If not, tell the user to run `gh auth login`.
   - `git rev-parse --abbrev-ref HEAD` — current branch. If it equals the base branch, stop
     (nothing to PR).
   - `git status --porcelain` — if there are uncommitted changes, stop and ask the user to
     commit or stash first (this skill does not commit for them).
   - `git rev-parse --verify origin/<base_branch>` — the base must exist on origin.
3. **Gather context** — run in parallel:
   - `git diff --name-only origin/<base_branch>...HEAD` — changed files
   - `git log origin/<base_branch>...HEAD --oneline` — commit history
4. **Read the diffs** — for each changed file run `git diff origin/<base_branch> -- <file>`
   and read the full file if needed for context. Skip binary files and `.meta` files.
5. **Synthesise** — from the commits and diffs, identify:
   - The primary goal of the branch (one sentence)
   - The key changes grouped by theme (new features, fixes, refactors, tests, docs)
   - Any breaking changes to public API
6. **Build two temp files** (e.g. in the scratchpad dir, so the CLI never has to escape
   text):
   - `pr-body.md` — the **PR Body Format** below
   - `squash-body.md` — the **Squash Commit Message** body (the `-` bullet list only, no
     subject line, no section headers)
7. **Push the branch** — `git push -u origin HEAD` (no-op if already up to date).
8. **Create or update the PR** on `origin`:
   - Check for an existing one: `gh pr view --json url,number,state,isDraft` (scoped to the
     current branch).
   - **No open PR** → `gh pr create --repo <origin> --base <base_branch> --head <branch>
     --assignee @me --title "<title>" --body-file <pr-body.md>` (add `--draft` if requested).
   - **Open PR exists** → `gh pr edit <number> --add-assignee @me --title "<title>"
     --body-file <pr-body.md>`, and report that it was updated rather than created. Do not
     toggle draft state on an existing PR unless `--draft` was passed and it differs.
   - `--dry-run` → skip steps 7–9 entirely; print the title, the rendered PR body and the
     squash message to the terminal.
9. **Merge the PR** (skip if `--no-merge`, `--draft`, or `--dry-run`):
   - **Repo merge gate.** If the repo's `CLAUDE.md` or contributing docs define a
     pre-merge gate (a PR-body section that must record a pass, a required sign-off), honour
     it: if the gate is unmet, **do not merge** — stop, leave the PR open, and tell the user
     what the gate requires. If the repo defines no such gate, skip this step.
   - `gh pr merge <number> --repo <origin> --squash --subject "<title>"
     --body-file <squash-body.md> --delete-branch`
   - If the merge fails because the PR is **not mergeable** (conflicts, branch behind base,
     or a required check failing), stop: report why, leave the PR open, and tell the user
     what to resolve. Do not force anything.
   - On success, sync local: `git checkout <base_branch> && git pull --ff-only`, then
     `git branch -d <branch>` (the local copy; the remote branch is already deleted).
10. **Report** — the PR URL, whether it was created or updated, the merge result (merged +
    the new `<base_branch>` commit hash, or "left open" with the reason), and — only when the
    PR was **not** merged — the full **Squash Commit Message** block for a manual merge.

## PR Body Format

The PR title (passed via `--title`, not in the body):

```
<title — imperative mood, under 60 chars, e.g. "Add drag and rotation to puzzle pieces">
```

The PR body (`pr-body.md`, passed via `--body-file`):

```
### What
<2–6 bullet points describing what changed and why>

### How
<2–6 bullet points on the implementation approach — key design decisions worth calling out>

### Testing
<1–6 bullet points: what tests were added and what they cover>

<Any PR-body section the repo's merge gate requires (see step 9) goes here, in the form
that gate specifies. Omit if the repo defines no such gate.>

### Notes
<Optional: breaking changes, known limitations, follow-up work>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Squash Commit Message

Its **body** (`squash-body.md`) is passed to `gh pr merge --body-file` and becomes the
squashed commit's body; its **subject** is the PR title, passed via `--subject`. When the
PR is not merged, print the whole block to the terminal instead:

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
- Keep the `🤖 Generated with [Claude Code]` footer as the last line of the PR body (repo
  convention for PRs)
- Squash commit subject: identical to the PR title (already imperative, under 60 chars)
- Squash commit body: unordered list with `-`, 3–6 items, one idea per bullet, no section
  headers — just the key facts a future `git log` reader needs
- The PR is always assigned to the current gh user (`--assignee @me`)
- Default is squash-merge + delete branch; `--no-merge` / `--draft` open the PR without
  merging
- Never force-push, rewrite history, or force a non-mergeable PR through; never create or
  merge against a remote other than `origin`
- Never merge past an unmet repo merge gate (see step 9)
