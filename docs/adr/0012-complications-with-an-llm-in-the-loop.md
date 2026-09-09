---
Status: accepted
Date: 2026-09-09
---

# 0012. How complications work when the code is written with an LLM

The narrative's beats each carry a **Complication** — a realistic failure the learner
investigates and diagnoses. That format assumes the failure arrives by accident: the
learner writes code, a subtle bug rides along, and debugging it is the exercise. Beacon is
built pair-programming with an LLM, so that assumption does not hold — application and
config code arrives correct on the first pass, and a deliberately injected bug is both
artificial and defeated the moment the learner asks the assistant what is wrong.

## Decision

Complications are split into two kinds, and beats are written accordingly.

- **Operational complications** stay, and are diagnosed live. These are failures where the
  build is correct and the system still misbehaves because of how the parts fit together:
  an image never loaded into kind, a Service `targetPort` mismatch, a stale ReplicaSet
  still serving, a `kubectl` context pointing at the wrong cluster, a readiness probe that
  flaps, a full PVC. An LLM writing the manifests does not spare the learner these, and
  they are what deployment-lifecycle interviews actually probe.

  They are diagnosed under **gauntlet rules** (the Beat 4.4 model, applied throughout):
  while the learner is diagnosing, Claude answers only *as the system would* — it returns
  `kubectl get/describe`, logs, events, and metric values in response to the right
  question, and does not volunteer the diagnosis or the fix. The learner writes the
  diagnosis first, in the issue or PR; then normal assistance resumes.

- **Code-level complications** are replaced by a **Failure modes** write-up in the PR body:
  the learner states what would break, why, and the signal they would see. Prediction
  instead of post-hoc discovery. This is at least as good as interview preparation, and it
  is not defeated by having an LLM in the loop.

A beat keeps a **Complication** field only where the complication is operational. Where the
original script had a code-level complication, the beat gets a **Failure modes** field
instead. The `docs/narrative.md` *Conventions* section carries the short version of this.

## Considered options

- **Keep every complication, inject the bug deliberately** — rejected. Artificial, and the
  learner can dissolve it by asking the assistant.
- **Drop complications entirely** — rejected. The diagnosis skill is a committed learning
  objective and the single most interview-relevant one.
- **Split by kind (this ADR)** — chosen. Keeps the failures that survive LLM-assisted
  development as live exercises; converts the rest into an articulation exercise.

## Consequences

- Beats are amended lazily, as they are played, per the existing "amend on divergence"
  convention — not rewritten ahead of time. Beat 1.2 is amended now as the worked example.
- The PR body becomes the place a beat's failure-mode analysis lives (consistent with
  CLAUDE.md: "put diagnosis detail worth keeping in the PR body").
- "Gauntlet rules" is now a named mode that applies whenever the learner is mid-diagnosis,
  not only in Act 4. Claude withholding the answer during diagnosis is expected behaviour,
  not the assistant being unhelpful.
