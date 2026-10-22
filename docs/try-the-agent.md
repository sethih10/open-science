# Try the agent

One study, start to finish, in the Claude Code chat: the example \*OH → \*O + \*H on Pt(111) with EMT, a test potential, so the run is about seeing the agents work, not about Pt. You talk to one agent, the orchestrator. It hands work to the six specialists, shows you the structures, and asks you everything in Claude Code's question box; you answer by clicking, and code records each answer under your name.

| You need | Check |
|---|---|
| The repository with its `.venv`, once: `python3 -m venv .venv && .venv/bin/pip install -e ".[structures,agents,dev,figures]"` | `.venv/bin/fragplace registry` lists 20 tools |
| A Claude Code login, in the VS Code extension or the terminal | `claude --version` |
| The plugin enabled for the repository and, on a cluster, `FRAGPLACE_SRUN`, both in `.claude/settings.local.json` as the README's *How to use* shows | `/mcp` in the chat lists `plugin:fragplace:fragplace` as connected |

| Cost of one study | Value |
|---|---|
| Wall time | about 25 minutes of agent work with EMT, plus yours at the five checkpoints; each heavy step waits for a compute node first |
| Claude usage | about 8 US dollars, most of it the scientific-critic reading records |

## 1. Start

In the chat, type:

```text
/fragplace:study demo
```

The orchestrator reads its page, finds no study called demo and asks what to run on. Choose the example; it runs `fragplace init demo --example` itself, which builds the three inputs with EMT and a `PROJECT.md` of test values. With your own files it asks for their paths, their format and the bond to break, A's side first, and runs `fragplace init` with them.

## 2. Answer as it goes

| The orchestrator | You |
|---|---|
| Asks the five interview questions of `PROJECT.md`, each with answers the computational-chemist drafted | Pick one or write your own under Other; the answer lands in the Interview table of `PROJECT.md` |
| Asks for any open decision still missing; the example has none | Pick a value from the options, each with its source, or write another |
| Opens the inputs, then shows the settings the computational-chemist proposed and the published values the literature-reader found; the example runs no DFT, so the lock is protocol mlip: the cell, the force threshold and the gas references, with one line saying the potential computes every energy, and no question about a functional, cutoff or k-mesh | Approve settings; tick the values you checked against their source |
| Shows the potential the mlip-specialist chose, the compute plan the hpc-specialist proposed from `compute_plan`'s estimate, with the lane, cores, memory and time of each heavy step and why, and the scientific-critic's review | Approve the plan, the compute plan with it; it cannot change after this box |
| Runs sites, pairs, placement, the pull-force screen, the surface-chemist's ordering, the gate, relaxation, the gate again and clustering; after each step it shows the step's summary and opens its pictures in your editor | Look; ask anything, such as why the surface-chemist chose its order |
| Shows the doubt flags | Approve, or choose Change something and say which candidates to drop |
| Opens the ranked final states and asks which to keep | Tick up to five |
| Writes the report, has the critic review it, shows the whole summary | Approve with your interpretation in the note |

Interview answers to try, from our trial:

```text
1. Whether the adsorbate stayed on its site, and whether slab and adsorbate were computed with the same settings.
2. EMT for anything with O and H: it is a test potential only.
3. Its E_ads error on the supplied inputs; for this dry run I accept EMT as a test potential.
4. None for this dry run.
5. H left on a bridge or top site, a saddle point, after relaxation.
```

The orchestrator cannot answer its own question box, edit a record or run `fragplace approve`; the hooks block each, and only your answer passes a checkpoint. Stop whenever you like with Stop here; the same command later resumes where the study stands.

## 3. Look at what it did

| File, under `runs/demo/` | What to look for |
|---|---|
| `summary.md` | One short block per step: what came out, the numbers, the files |
| `geometries/` | A folder per step: `.xyz` files and pictures; `4-relaxed/` has the start and end of every candidate and a contact sheet |
| `report.md` | The steps in brief, the final states with both energies, every survivor and rejection with its reason, the open decisions, your choices and interpretation, and what each agent said |
| `trace.jsonl` | Every tool call, decision and answer, each under its actor: a tool, an agent or you |
| `PROJECT.md` | The locked settings, the decisions with who set them, your interview answers |

Who acted, counted from the trace:

```bash
python3 -c "import json,collections; print(collections.Counter(json.loads(l)['actor'] for l in open('runs/demo/trace.jsonl')))"
```

## 4. Check it without the agents

| Check | Command | Cost |
|---|---|---|
| The tools, the hooks and the question boxes | `python -m pytest -q` on a compute node | none |
| The pipeline as the test harness, every agent's choice replaced by a fixed rule | `fragplace init scripted --example`, then `fragplace run scripted` and the `fragplace approve` each stop prints, five times | none |

## When something goes wrong

| You see | Why | Do |
|---|---|---|
| `/fragplace:study` is unknown | The plugin is not enabled for the repository | Add the keys of the README's *How to use* to `.claude/settings.local.json` and reopen the chat |
| `plugin:fragplace:fragplace` failed in `/mcp` | The `.venv` is missing or the package is not installed in it | `ls .venv/bin/fragplace-server`; install as in the first table |
| A failed server named `fragplace` | The repository's `.mcp.json` read a second time | Put `"disabledMcpjsonServers": ["fragplace"]` in `.claude/settings.local.json` |
| A step waits a long time | The heavy tools wait for a compute node through `FRAGPLACE_SRUN` | `squeue -u $USER`; a busy partition delays each heavy step |
| Every step is very slow and `FRAGPLACE_SRUN` is unset | The tools run on the login node | Set `FRAGPLACE_SRUN` and reopen the chat |
| A tool answers `blocked` with a question box | A checkpoint is yours and has not been passed | The orchestrator asks it; answer |
| `You've hit your session limit` | Your Claude usage ran out | After the reset, type `/fragplace:study demo` again; the study keeps its state on disk |
