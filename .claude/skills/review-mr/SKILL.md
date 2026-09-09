---
name: review-mr
description: Reviews the current branch against master for code efficiency, consistency, refactoring opportunities, and best practices. Outputs a detailed markdown review report.
---

Reviews the current branch against `master` (or a specified base branch) for code efficiency, consistency, refactoring opportunities, and best practices. Outputs a detailed markdown review report.

**Arguments** (optional, passed as `$ARGUMENTS`):
- `--base-branch <branch>` — Compare against this branch (default: `master`)
- `--output-file <path>` — Where to save the review (default: `./mr-review.md`)
- `--focus <areas>` — Comma-separated: `efficiency`, `consistency`, `refactoring`, `security`, `tests`, `docs` (default: all)

## Execution Steps

1. **Parse arguments** from `$ARGUMENTS` — extract `--base-branch`, `--output-file`, `--focus` if provided; fall back to defaults
2. **Get changed files** — run `git diff --name-only <base_branch>...HEAD`
3. **Get current branch name** — run `git rev-parse --abbrev-ref HEAD`
4. **Analyze each changed file**:
   - Read the full file for context
   - Review the diff with `git diff <base_branch> -- <file>`
   - Identify efficiency issues, inconsistencies, and refactoring opportunities
5. **Write the markdown report** to the output file using the format below

## Review Focus Areas

### Efficiency
- Unnecessary iterations or nested loops
- Redundant calculations or allocations
- Unoptimized data structures
- Missing caching/memoization opportunities

### Consistency
- Code style mismatches with surrounding code
- Naming convention violations (`Piece_{row}_{col}` format in this project)
- Inconsistent error handling patterns
- Different approaches to similar problems

### Refactoring
- Duplicated code blocks (DRY violations)
- Functions doing too much (single responsibility)
- Magic numbers/strings without constants
- Complex conditionals that could be simplified

### Security
- Input validation gaps
- Unsafe operations
- Credential/secret exposure

### Tests
- Missing unit tests for new functions
- Edge case coverage gaps
- Test quality and maintainability

### Docs
- Missing docstrings or comments for complex logic
- plan/ and Documentation~/ consistency (required by CLAUDE.md)
- Breaking change documentation

### Erroneous Inclusions
- Debug/investigation files committed by mistake (e.g. `debug-*.md`, `*.log`, `*_debug.txt`)
- Temporary or scratch files that have no place in the final codebase
- Binary assets or generated files that should be in `.gitignore`
- Test fixtures, sample outputs, or one-off scripts that were used during development but not cleaned up
- `.meta` files for assets that no longer exist

### System Design
- Whether new code fits the existing architectural boundaries (Core vs. Unity layer separation, static vs. instance responsibilities)
- Abstraction level mismatches — logic placed in the wrong layer (e.g. Unity concerns leaking into Core)
- Public API surface changes — new public types or methods that increase coupling or complicate future changes
- Whether the change introduces any tight coupling that will make future M3+ features harder to add
- Data flow clarity — are inputs, outputs, and side effects of each function clear and consistent with surrounding code?

## Output Format

Write the review to the output file in this format:

```markdown
# Code Review: [branch] vs. [base_branch]

**Branch**: [current-branch-name]
**Base**: [base-branch-name]
**Date**: [today's date]
**Status**: [Approved / Changes Requested / Comment]

## Summary
[Brief overview of the changes and their impact]

## Files Reviewed
- `file1.cs` — [2 efficiency issues, 1 style issue]
- `file2.cs` — [1 refactoring opportunity]

## Code Efficiency Issues
### [File:LineNumber] — [short title]
- **Problem**: [description]
- **Impact**: [performance impact]
- **Suggestion**: [concrete fix]

## Inconsistencies & Style Issues
### [File:LineNumber] — [short title]
- **Problem**: [description with code context]
- **Expected**: [how it's done elsewhere in the codebase]
- **Suggestion**: [specific change]

## Refactoring Opportunities
### [File:LineNumber-LineNumber] — [short title]
- **Pattern**: [description]
- **Suggestion**: [refactoring approach]
- **Benefit**: [why it matters]

## Security & Best Practices
[Any critical concerns, or "None identified."]

## Testing & Documentation
[Coverage assessment and documentation gaps]

## Overall Assessment
**Recommendation**: [Approve / Request Changes / Comment]
- Strengths: [list]
- Areas for Improvement: [list]
```

## Notes

- Always provide specific line numbers and file links
- Be constructive — include concrete suggestions, not just criticism
- Consider the PR's scope — don't suggest unrelated refactorings
- Prioritize findings: critical security/correctness → efficiency → style/consistency
- For this project, verify plan/ and Documentation~/ stay consistent (per CLAUDE.md)
