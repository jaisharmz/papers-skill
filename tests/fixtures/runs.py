"""Two runs: one that should pass every check, one that fails each on purpose.

The bad run's failures are the ones observed in the first real test run, so this
is a regression fixture rather than an invented one.
"""

GOOD = {
  "meta": {"title": "Masked diffusion",
           "opening": "Three steps into masked diffusion language models."},
  "entries": [
    {"position":1,"id":"a","kind":"paper","group":"g1","title":"A",
     "summary":"Argues the objective decomposes over orderings, which reframes the model class as any-order autoregressive rather than a separate family with its own theory.",
     "unlocks":"After this the later order-learning papers read as one argument.",
     "where_the_thinking_is":"The decomposition in equations 4 to 9.",
     "question":"What does the framing still buy at inference?",
     "conditioning":"Position one because it reframes what you already built."},
    {"position":2,"id":"b","kind":"repo","group":"g1","title":"o/r",
     "summary":"Reference implementation.",
     "unlocks":"The base for the project below.",
     "where_the_thinking_is":"`model/sampler.py`, the sixty lines under `def step`, commit a3f21c9.",
     "conditioning":"Right after its paper because reading the mask as code takes twenty minutes."},
    {"position":3,"id":"c","kind":"project","group":None,"title":"C",
     "summary":"Measure throughput against a matched baseline yourself.",
     "unlocks":"A number nobody has published for your hardware.",
     "where_the_thinking_is":"The step where you pick the quality bar.",
     "conditioning":"At three because one and two leave the hardware question open."}],
  "groups":[{"slug":"g1","name":"G","institution":"Cornell Tech, observed on the 2025 paper",
             "thesis":"Keep the diffusion objective and recover what AR gets for free.",
             "thesis_source":"https://arxiv.org/abs/2506.01928",
             "read_more":[{"label":"paper","url":"https://arxiv.org/abs/2506.01928"}]}],
  "ideas":[{"name":"i1","experiential":False},{"name":"i2","experiential":True}],
  "confidence":{"unverified":["one affiliation could not be dated"]}}

BAD = {
  "meta": {"title": "Masked diffusion, after the objective stops mattering"},
  "entries": [
    {"position":1,"id":"a","kind":"paper","group":"ghost","title":"A",
     "summary":"This document explores a robust framework.","unlocks":"x",
     "where_the_thinking_is":"","conditioning":""},
    {"position":2,"id":"b","kind":"repo","group":"g1","title":"o/r",
     "summary":"y","unlocks":"y",
     "where_the_thinking_is":"https://github.com/o/r",
     "conditioning":"A good repo."},
    {"position":3,"id":"c","kind":"paper","group":"g1","title":"C",
     "summary":"z","unlocks":"z",
     "where_the_thinking_is":"Read section 4.","conditioning":"It is next."}],
  # thesis_source present on purpose: without it the unsourced-thesis branch
  # fires too and the placeholder check cannot be told apart from it.
  "groups":[{"slug":"g1","name":"G","institution":"Cornell",
             "thesis":"Placeholder. A full run reads this off their papers.",
             "thesis_source":"https://arxiv.org/abs/1"}],
  "ideas":[{"name":"i1","experiential":True}],
  "confidence":{"unverified":[]}}
