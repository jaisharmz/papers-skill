---
# Copy to ~/.claude/papers/profile.md and edit. Nothing about you belongs
# anywhere else in this repository: swap this file and the skill runs unchanged.
name: Your name
level: >
  One paragraph on the register to write at. "Reads math-heavy papers natively
  and implements from them, never define standard machinery" produces a very
  different path from "comfortable with the vocabulary, still learning the math".
trajectory: undecided | phd | industry
infra:
  compute: What you can actually run. A few GPUs for days? One laptop? A cluster?
  comfortable: [PyTorch, JAX, whatever you reach for without thinking]
  unfamiliar: [CUDA kernels, robotics hardware, wet lab, anything you have never touched]
# A folder of PDFs. This is the single highest-value line in the file: it is the
# INITIAL STATE of the selection, not an exclusion list, so the path starts where
# your knowledge stops instead of starting over.
reading_log: /path/to/your/papers/
---

# Profile

## Deep

Areas to treat you as a peer in. Reading lists here start after the canon.
Name what you have actually implemented, not what you have read about.

## Touched

You know the vocabulary and can read the papers, and would still learn from depth.

## Untouched

Genuine greenfield. The adjacent region weights toward these, because a collision
between two things you know nothing about is the most valuable thing a run finds.

## Constraints

Deadlines, hours available, and what output is worth more to you: something
publishable, or something that only produces understanding.
