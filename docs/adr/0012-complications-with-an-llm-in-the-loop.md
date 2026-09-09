---
Status: accepted
Date: 2026-09-09
---

# 0012. How complications and assessment work with an LLM in the loop

The narrative's beats each carry a **Complication** — a realistic failure the learner
investigates and diagnoses. That format assumes the failure arrives by accident: the
learner writes code, a subtle bug rides along, and debugging it is the exercise. Beacon is
built pair-programming with an LLM, so that assumption does not hold. Application and config
code arrives correct on the first pass; a deliberately injected bug is artificial and is
defeated the moment the learner asks the assistant what is wrong.

The same problem defeats every mechanism phrased as *"the learner writes X"* — a
failure-mode prediction, a design note, the PR body itself. If the output is text in the
repo, the LLM can produce it. The one thing that cannot be outsourced is the learner being
asked a question and answering it, unaided, out loud.

## Decision

### Operational complications stay, diagnosed live under gauntlet rules

Failures where the build is correct and the system still misbehaves because of how the
parts fit together — an image never loaded into kind, a Service `targetPort` mismatch, a
stale ReplicaSet still serving, a `kubectl` context pointing at the wrong cluster, a
readiness probe that flaps, a full PVC. An LLM writing the manifests does not spare the
learner these.

While the learner is diagnosing, Claude answers only *as the system would* — it returns
`kubectl get/describe`, logs, events, and metric values in response to the right question,
and does not volunteer the diagnosis or the fix. The learner states the diagnosis first;
then normal assistance resumes. These are **gauntlet rules**, and they apply whenever the
learner is mid-diagnosis, not only in Act 4.

### Code-level complications are replaced by a Checkpoint

Every beat ends with a **Checkpoint**: after the code is done and **before the PR merges**,
Claude questions the learner on what was built, why it is shaped that way, and what would
break. The learner answers in chat, cold: no reading the diff first, no help from Claude.
Claude then assesses each answer honestly and names the gaps. Weak answers can be re-run
after the learner reads up.

The exchange is interactive: **one question at a time**, Claude waiting for each answer
before asking the next, roughly four to six in total — never the whole list up front. When
Claude reports the assessment it **pairs each question with the learner's answer and the
verdict**, shown together, so the learner never has to scroll back to see what was asked.

- **A weak checkpoint blocks the merge.** The PR does not squash-merge until the checkpoint
  is passed. This is the one place the project gates on understanding rather than on a
  green check.
- **It is recorded in the PR body.** Claude writes a short *Checkpoint* section — the
  questions asked, a one-line verdict per answer, and the gaps found and closed. Claude
  authors it, but as a factual record of the exchange, not a prediction the learner is
  pretending to have written.
- **Gauntlet rules apply during it.** Claude asks and assesses; it does not teach. Teaching
  happens before (building) and after (working through the gaps).

## Considered options

- **Keep every complication, inject the bug deliberately** — rejected. Artificial, and the
  learner can dissolve it by asking the assistant.
- **Learner writes a failure-mode prediction in the PR body** — rejected. The learner does
  not hand-write PR bodies; Claude would end up writing the prediction too.
- **Drop complications and assessment entirely** — rejected. The ability to explain and
  defend the system is the single most interview-relevant outcome of the project.
- **A live Checkpoint that gates the merge (this ADR)** — chosen. The only mechanism that
  tests the learner rather than the assistant.

## Consequences

- The `/create-pr` flow gains a precondition: do not merge until the PR body has a
  *Checkpoint* section recording a pass. `.claude/skills/create-pr/SKILL.md` carries this.
- Beats are amended lazily, as they are played, per the existing "amend on divergence"
  convention. A beat keeps a **Complication** field only where the complication is
  operational; every beat gains a **Checkpoint** field listing what the questioning covers.
  Beat 1.2 is amended now as the worked example.
- `docs/narrative.md` → *Conventions* carries the short version; `CLAUDE.md` carries the
  operating instructions for Claude.
- "Building fast with the LLM" is no longer in tension with the learning goal — the
  Checkpoint is where the learning is verified, so the build can be as assisted as it likes.
