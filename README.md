# open-science-hackathon

An AI agent that computes adsorption energies on catalyst surfaces reliably, and knows when not to trust itself. Start with [docs/adsorption-agent-workflow.md](docs/adsorption-agent-workflow.md).

## Layout

```
.
├── README.md                          this file
├── CLAUDE.md                          agent instructions (imports docs/CLAUDE.md)
└── docs/
    ├── README.md                      how to view the docs
    ├── CLAUDE.md                      when agents update which file
    ├── adsorption-agent-workflow.md   the design doc for people: science, workflow, prior work, strategy, decisions
    ├── agent-context.md               the same for agents: text only, no figures
    ├── agent-build-context.md         what to build: tools, formats, rules, order, open decisions
    ├── repo-survey.md                 repositories to wrap or copy, licences, recommended stack
    ├── agent-writing-style.md         how agents write and draw for this project
    └── figures/                       PNG figures for the design doc, numbered in reading order
        └── src/                       matplotlib scripts for figures 13 to 24
```
