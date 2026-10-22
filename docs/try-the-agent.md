# Try the agent

One campaign, start to finish, with the agents in Claude Code: the example *OH → *O + *H on Pt(111) with EMT, a test potential, so the run is about seeing the agents work, not about Pt. You type into one Claude Code session; the solution-planner answers, hands work to the other agents, asks you what it needs, and stops five times for your approval.

| You need | Check |
|---|---|
| The repository with its `.venv`, once: `python3 -m venv .venv && .venv/bin/pip install -e ".[structures,agents,dev,figures]"` | `.venv/bin/fragplace registry` lists 19 tools |
| A Claude Code login | `claude --version` |
| A compute node; the tools must not run on the login node | `srun -p interactive -c 4 --mem=8G --time=2:00:00 --pty bash` |

| Cost of one campaign, from our trial | Value |
|---|---|
| Wall time on 4 CPUs | about 25 minutes of the agents working, plus yours at the five stops |
| Claude usage | about 8 US dollars, most of it the scientific-critic reading records |

## 1. Start

On the compute node, from the repository:

```bash
source .venv/bin/activate
export FRAGPLACE_ROOT=$PWD/runs/_demo      # campaigns and their case bank go here, outside the repository's lessons.md
fragplace init demo --example              # the three inputs relaxed with EMT, PROJECT.md with test values
claude --plugin-dir .
```

Claude Code starts with the plugin. A failed server named `fragplace` may show at the start; it is the repository's `.mcp.json` read a second time, and the plugin's own copy, `plugin:fragplace:fragplace`, is the one that runs.

## 2. Run the campaign

Type `/fragplace:campaign demo`. Then answer as the table says. After each `!` command, type `done, continue`.

| The agent does | You type |
|---|---|
| Reads the campaign and asks the five interview questions of `PROJECT.md` | The answers below, or your own |
| Asks for any open decision still missing; the example has none | A value and a reason; the agent records it with `fragplace decide`; allow the command when Claude Code asks |
| Sends the literature-reader to look for published values; from Triton it finds none and says why | Nothing |
| Runs `structure_retrieval`; the computational-chemist picks the protocol; stops at **approve settings** with the settings | `! fragplace approve demo "approve settings" --who <you> --reason "dry run with EMT"` |
| The mlip-specialist picks the potential; the scientific-critic reviews the plan; stops at **approve the plan** | `! fragplace approve demo "approve the plan" --who <you> --reason "<your answer to the critic>"` |
| Sites, pairs, placement, the pull-force screen; the surface-chemist orders the candidates from their cards; relaxation, the gate, clustering, the doubt; stops at **review flagged cases** | `! fragplace approve demo "review flagged cases" --who <you> --reason "keep all"` |
| Ranks the survivors with their cards; stops at **pick up to five final states** | `! fragplace approve demo "pick up to five final states" --who <you> --chosen <ids from its table> --reason "..."` |
| Reference energies and the report; the scientific-critic reviews the report; stops at **interpret results** | `! fragplace approve demo "interpret results" --who <you> --reason "<what you conclude>"` |

Interview answers to paste, from our trial:

```text
1. Whether the adsorbate stayed on its site, and whether slab and adsorbate were computed with the same settings.
2. EMT for anything with O and H: it is a test potential only.
3. Its E_ads error on the supplied inputs; for this dry run I accept EMT as a test potential.
4. None for this dry run.
5. H left on a bridge or top site, a saddle point, after relaxation.
```

The agent never runs `fragplace approve` itself; the hooks block it if it tries, and only your `!` command passes a checkpoint. Ask it anything between the steps, such as why the surface-chemist chose its order; it answers from the cards and the trace, never from coordinates.

## 3. Look at what it did

| File, under `runs/_demo/runs/demo/` | What to look for |
|---|---|
| `report.md` | The final states with E(FS near), E(FS ∞) and the lateral interaction; every rejected pair with its reason; your choices; at the end, what each agent said |
| `trace.jsonl` | Every tool call and every decision, each under its actor: a tool, an agent or you |
| `cards/*.txt`, `cards/*.png` | The descriptor card of each candidate, the only view of geometry the agents had |
| `PROJECT.md` | The locked settings, the decisions and who set them |

Who acted, counted from the trace:

```bash
python3 -c "import json,collections; print(collections.Counter(json.loads(l)['actor'] for l in open('runs/_demo/runs/demo/trace.jsonl')))"
```

In our trial the five agents of the core each appear, beside about five hundred tool entries and your approvals.

## 4. Check it without the agents

| Check | Command | Cost |
|---|---|---|
| The tools and the rollout | `python -m pytest -q`, 144 tests in under a minute | none |
| The same campaign as a script, the agents' choices replaced by fixed rules | `fragplace init scripted --example`, then `fragplace run scripted` and the `fragplace approve` each stop prints, five times | none |
| The plugin loads and one tool answers through Claude Code | `claude -p "Call the fragplace tool campaign_status for campaign demo and reply with its next field." --plugin-dir . --allowedTools mcp__plugin_fragplace_fragplace ToolSearch` | about 0.25 US dollars |

## When something goes wrong

| You see | Why | Do |
|---|---|---|
| `fragplace: command not found` after `!` | Claude Code was started without the `.venv` active | Quit, `source .venv/bin/activate`, start again with the same `FRAGPLACE_ROOT` |
| No fragplace tools; `plugin:fragplace:fragplace` failed | The `.venv` is missing or the package is not installed in it | `ls .venv/bin/fragplace-server`; install as in the first table |
| A tool answers `blocked` with a checkpoint | That checkpoint is yours and has not been passed | Run the `fragplace approve` command it shows |
| A tool answers `open_decision` | A value marked open: team decision is missing | Give the agent the value and a reason |
| Every step is very slow | The session runs on the login node | Start again on a compute node |
| `You've hit your session limit` | Your Claude usage ran out | Resume after the reset with `claude --plugin-dir . --continue`; the campaign keeps its state on disk |
