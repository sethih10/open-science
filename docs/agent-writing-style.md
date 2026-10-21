# Agent writing style for this project

Audience: an agent writing or editing anything in this repository: the design document, the agent context, figures, skill files, code comments, commit messages. Rules on *when* to write are in `CLAUDE.md`; what the project knows is in `agent-context.md`.

## Prose

- Lead each section with its conclusion in one sentence, then the reasons.
- Short declarative sentences, no hype.
- Give every step a single owner: Tool, LLM, Human, or Literature.
- Cite new sources in *Sources* with a link.
- Never use em-dashes or parentheses in running prose; use a comma, a colon or a new sentence.
- Numbers belong in tables or equations, not in running prose, unless they change what the reader does.
- Do not invent sources. Cite only what was read; mark anything from memory as "from memory, not looked up here".
- British spelling: optimise, colour, judgement, centre.

## Figures, tables and equations

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
- Restate what the figure shows in `docs/agent-context.md` as a table, list or rule; never link the image there.

## Writing for agents (`agent-context.md`)

- Text only. No image links, no "reading the figure" paragraphs.
- Restate each figure as the lightest text form that carries it: a table for layouts and mappings, a numbered list for flows, a rule for a single constraint, a worked example for a counting argument.
- State facts as rules an agent can apply: thresholds, units, owners, triggers. "Reject an adsorbate more than 3 Å above the surface", not "adsorbates sometimes desorb".
- Keep section numbers stable; other files refer to them.
- Decisions are listed as locked; open questions as questions; next steps as `- [ ]` items. Mirror the human document exactly.
- Sources live in the human document only; the context file points there.

## Commit messages

- First line: imperative, under 60 characters, says what changed in the docs or code.
- Body: one line per file group on what and why; no changelog of the conversation.
