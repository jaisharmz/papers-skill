"""A hand-built candidate set where I know the right answer.

Six ideas. i_obj (why this objective), i_fail (the failure mode, EXPERIENTIAL:
only a project covers it), i_trick (what made it work), i_bench (what the
benchmark misses), i_disagree (the live argument, coverable only by the pair),
i_scale.
"""
from scripts.ordering import Item

ITEMS = [
    Item(id="survey", year=2021, phrase='organises what already exists', kind="paper", title="A Survey of Everything",
         covers={"i_obj": .5, "i_trick": .4, "i_bench": .4, "i_scale": .4},
         cost_hours=3, depth_payoff=.15, role="survey"),
    Item(id="seminal", year=2019, phrase='named the problem and the objective', kind="paper", title="The Paper That Started It",
         covers={"i_obj": .95, "i_trick": .3}, cost_hours=3, depth_payoff=.9,
         role="seminal"),
    Item(id="modern", year=2025, phrase='the current best method', kind="paper", title="The Current Best Method",
         covers={"i_trick": .8, "i_scale": .7}, cost_hours=2.5, depth_payoff=.8,
         requires=["seminal"], role="result"),
    Item(id="repo_nano", year=2025, phrase='the whole loop in one sitting', kind="repo", title="nano-thing",
         covers={"i_trick": .95, "i_fail": .3}, cost_hours=2, depth_payoff=.85,
         role="readable-reimplementation", requires=["modern"]),
    Item(id="repo_dump", year=2024, phrase='the official release, pushed once', kind="repo", title="official-release",
         covers={"i_trick": .5}, cost_hours=2, depth_payoff=.2,
         role="research-dump"),
    Item(id="bench", year=2022, phrase='defines how the field scores itself', kind="paper", title="The Benchmark",
         covers={"i_bench": .9}, cost_hours=1.5, depth_payoff=.4, role="benchmark"),
    Item(id="pos_a", year=2024, phrase='argues scale settles it', kind="paper", title="Scaling Is All You Need",
         covers={"i_scale": .8, "i_disagree": .5}, cost_hours=2, depth_payoff=.7,
         role="position", disputes=["pos_b"]),
    Item(id="pos_b", year=2025, phrase='argues scale does not settle it', kind="paper", title="Scaling Is Not All You Need",
         covers={"i_disagree": .95}, cost_hours=2, depth_payoff=.7,
         role="position", disputes=["pos_a"]),
    Item(id="proj_1", year=None, phrase='reproduce the headline number yourself', kind="project", title="Reproduce the headline number",
         covers={"i_fail": .9, "i_trick": .6}, cost_hours=14, depth_payoff=.95,
         requires=["repo_nano"], role="reimplement"),
    Item(id="proj_2", year=None, phrase='run it on the other dataset', kind="project", title="Run it on the other dataset",
         covers={"i_fail": .95, "i_bench": .7}, cost_hours=14, depth_payoff=.9,
         requires=["proj_1"], reuses=["proj_1"], role="apply"),
]
IDEA_WEIGHTS = {"i_obj": 1.2, "i_fail": 1.4, "i_trick": 1.0,
                "i_bench": .9, "i_disagree": 1.1, "i_scale": .8}
