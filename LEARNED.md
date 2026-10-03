# Learned — papers

Corrections this skill has earned in use. Read before running it; these override
`SKILL.md`. Protocol: `kernel/skill-learning.md`.

- **2026-09-25** — Citation counts: OpenAlex arXiv-DOI records undercount papers with a published version (Donut 5 vs 599); use the Semantic Scholar batch endpoint, which merges versions, retried in the background, and label the source
- **2026-09-25** — Fix the idea vocabulary in a file before the first reader launches; readers launched on a draft list scored six later ideas at zero and needed evidence-backed overrides
- **2026-09-25** — Trim coverage weights under 0.25 before ordering: a passing mention on a repo 'opened' an idea and the paper that measures it was filed under an unrelated subgroup
- **2026-09-25** — A system python3 can be too old for these scripts (3.7 on one Mac: it has PyYAML but lacks removesuffix). Run skill scripts with a python3 of 3.9 or newer, such as Homebrew's /opt/homebrew/bin/python3.13, and fall back to the older one only where PyYAML is missing
- **2026-09-25** — When the reader asks for methods per paper, the page must show a method line on every row, not only position one; build_page.py now renders method, date and a why-here disclosure per row
- **2026-09-25** — Jai rejected the rendered page as 'notes an AI would take for AI's usage'. The page must lead with the field's few ideas, each with an intuition and a small made-up example, then evidence, then a short list with a plain one-line idea and method per item. File, function, commit and table references stay in the folder, never on the page. — promoted 2026-09-26 into SKILL.md step 6 and the presentation guideline
- **2026-10-02** — Before any paper is submitted, resolve every citation against the real source (arXiv, DOI, venue page) and confirm it supports the claim it is cited for. One unverifiable or AI-invented reference is enough for a venue to withdraw an acceptance.
