# Keep the docs in step with the thinking

`docs/adsorption-agent-workflow.md` is the shared memory of this project. A colleague or another Claude instance must be able to pick up the work from it alone, without the conversation. So **update it as ideas form, not at the end.**

## When to write

Update the doc in the same turn as any of these happen:

| Trigger                                   | Where it goes                                              |
|-------------------------------------------|------------------------------------------------------------|
| A new idea, method or design change       | The section it belongs to (add a section if none fits)     |
| A choice is made                          | *Decided so far*, as one bullet                            |
| An option is rejected                     | The relevant section, with one line on why                 |
| A question appears that we cannot answer  | *Open questions*                                           |
| A concrete task follows                   | *Next steps*, as `- [ ]`; tick it `- [x]` when done        |
| A step, owner or tool changes             | The workflow tables **and** the figure that shows them     |

Edit in place; do not append a changelog. If new thinking contradicts the doc, fix the old text so the doc never says two things.

## Show it, don't only tell it

Every substantial idea should be readable at a glance. Pick the lightest form that carries it:

1. **Table**: steps, owners, comparisons, mappings (see *The adsorption workflow*).
2. **Equation** in `$$ … $$`: any quantity we compute.
3. **Figure**: flows, layers, energy levels, geometry, anything with arrows or space.

Code blocks are for code only, never as a substitute for a diagram.

### Figure conventions (copy the existing ones)

- File: `docs/figures/NN-short-kebab-name.png`, numbered in reading order; keep the script that draws it as `docs/figures/src/NN-short-kebab-name.py`.
- Look: white background, rounded boxes with thin grey outlines, grey arrows, sans-serif text. **One** highlighted box (light blue fill, blue outline) marks what is new or what we build. Bold title line stating the takeaway. Mark schematics as "schematic, not to scale".
- In the Markdown, always in this order:

```markdown
![<the takeaway as a sentence>](figures/NN-name.png)

*Figure: <subject> · <qualifier, e.g. 4 levels, schematic>*

Reading the figure: <walk the eye left-to-right or top-to-bottom; say what each
colour, box and arrow means, and what the reader should conclude>.
```

- Add or update the figure count and list in `docs/README.md`.

## Writing style

- Lead each section with its conclusion in one sentence, then the reasons.
- Short declarative sentences, British spelling, no hype.
- Give every step a single owner: Tool, LLM, Human, or Literature.
- Cite new sources in *Sources* with a link.
