# Keep the docs in step with the thinking

`docs/adsorption-agent-workflow.md` is the shared memory of this project. A colleague or another Claude instance must be able to pick up the work from it alone, without the conversation. So **update it as ideas form, not at the end.**

`docs/agent-context.md` is the same content for agents: text only, no figures, each figure restated as a table, list or rule. Every change to the design doc is mirrored there in the same turn; the design doc is the source of truth when they differ.

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
| A top-level file or folder is added       | The *Layout* tree in the root `README.md`, one line each   |
| Any of the above                          | The matching section of `docs/agent-context.md`, text only   |

Edit in place; do not append a changelog. If new thinking contradicts the doc, fix the old text so the doc never says two things.

## How to write

Follow `docs/agent-writing-style.md`: prose rules, figure conventions, the text-only form for `agent-context.md`, and commit messages. The three agent files have one job each:

| File                          | Job                                                             |
|-------------------------------|-----------------------------------------------------------------|
| `docs/agent-context.md`       | What the humans know: the design document without figures       |
| `docs/agent-writing-style.md` | How to write and draw for this project                          |
| `docs/CLAUDE.md` (this file)  | When to update which file                                       |
