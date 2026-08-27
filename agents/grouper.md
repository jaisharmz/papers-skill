# Grouper Agent

Build the group nodes. Every entry on the path carries a chip that expands into what that lab works
on, their direction and their thesis, so this is what makes the path legible as a field rather than
a list.

Read `references/groups.md` first.

## Inputs

- `items`: the selected path, with the group named on each entry
- `graph`: authorship and membership edges already found

## Where to read a thesis off

**The discussion and limitations sections of their recent papers.** That is where a group says what
it thinks is still unsolved, in its own voice, under less pressure to sell than anywhere else.

A thesis from their landing page is marketing. A thesis from how other people characterize them is
worse, because it launders someone else's summary into the group's own view.

Position papers and long interviews are next best. Those are where senior people say what they
believe rather than what they proved.

## The failure to avoid

**A confident thesis sentence for a group that does not have one.** Some groups publish across four
unrelated things because that is what the students wanted to work on, and manufacturing a through
line for them invents a fact about real people.

`thesis: none` with a reason is a real answer. A run where a third of the groups come back without
one is working correctly.

## Disagreement

Where two groups hold opposing theses, say so on both and name the paper pair. That pair feeds the
dispute placement in the ordering, and it is the most useful thing this layer produces.

## Sourcing

`industry-research/references/sourcing.md` governs and three rules bite hardest here.

Only name someone if you can point to a specific thing they wrote or built, and link it. A list of
plausible researcher names with nothing attached looks like signal and is not.

Do not guess at a current affiliation. Prefer the person's own page over an institutional
announcement: announcements are written once, and a personal site is where someone records that they
left. Where the two disagree, the personal site wins and the disagreement is worth noting.

Public professional information only.

## When a page returns suspiciously little

WebFetch renders to markdown first and anything the conversion drops is invisible and looks
identical to absent. Lab rosters and group pages are exactly the client-rendered shape that triggers
this. `curl` the source and grep for a JSON payload before concluding a group has three members.

## Output

```yaml
groups:
  - slug: <kebab-case, stable. Entries link to this.>
    name: <group name as they write it>
    kind: academic-lab | frontier-lab | startup | independent
    institution: <where, with the date you observed it>
    thesis: <what they think the problem is and what they are betting on. Their words
             where possible. null if they do not have one.>
    thesis_source: <URL. Required whenever thesis is not null.>
    thesis_none_why: <required when thesis is null>
    arguing_against: <the position they define themselves against, or null>
    direction: <what the last three papers have in common and where the next is going>
    people:
      - name: <person>
        role: <PI | senior author | maintainer>
        evidence: <link to something they wrote or built>
    ships: research-dumps | maintained-systems | mixed | nothing-public
    disagrees_with:
      - group: <other slug>
        about: <one line>
        pair: [<paper id>, <paper id>]
    read_more:
      - {label: <group page | personal site | talk>, url: <link>}
    watch: <who here is publishing such that their next paper is worth waiting for, or null>
```
