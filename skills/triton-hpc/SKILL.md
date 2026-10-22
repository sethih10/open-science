---
name: triton-hpc
description: Where FragPlace's heavy calls run on Aalto's Triton cluster and with what resources: the partitions and their limits, Aalto's rules for agents, the decision table from interactive step to array of chunks, the held allocation, storage and network, monitoring, and what FragPlace's lanes do by themselves. Use at step 1* to propose the compute plan and whenever a heavy call fails with a Slurm state.
---

# Heavy calls on Triton

The hpc-specialist follows this; the orchestrator only receives its rules and diagnoses, and the human approves them with the plan. Code submits, polls and resubmits; the agent proposes and reads.

Every number below is from Triton's documentation or a measurement on 22 October 2026. A threshold marked inferred is our own estimate, not Aalto's, and gives way to a measured time.

## 1. Partitions

The scheduler picks the partition from the run time unless a rule names one: "Partition is automatically detected based on run time". GPU partitions reject a job that asks for no GPU.

| Partition | Nodes and cores | Memory per node | Longest job | Default time | Note |
|---|---|---|---|---|---|
| interactive | 7 nodes × 40 CPUs | 191 GB | 1 day | 2 h | no local disk; OverSubscribe FORCE:4, so CPU-bound relaxations may share cores four ways |
| batch-skl | 40 CPUs | 191 GB | 5 days | 15 min | the Slurm default |
| batch-csl | 40 CPUs | 191 GB | 5 days | 15 min | |
| batch-milan | 128 CPUs | 510 GB | 5 days | 15 min | |
| gpu-debug | | | 30 min | | one job per user |
| gpu-interactive | 3 × 4 V100-32G | | 4 h | | one job per user |
| gpu-h200-71g-ia | | | 8 h | 2 h | |
| GPU batch partitions | | | 5 days; 2 days for -short | | |

| Limit | Value |
|---|---|
| Jobs a user may have submitted, MaxSubmit | 30000 |
| Running CPU-minutes per user, GrpTRESRunMins | cpu=3000000 |
| CPUs a user gets on the login node | 2 |
| Default time and memory of a job | 15 min; 500 MB per CPU |

Always set `--time`, `--mem` and `-c` on every rule: the defaults kill a relaxation before it ends.

## 2. Aalto's rules for agents

Quoted from [Triton: AI agents](https://scicomp.aalto.fi/triton/usage/ai-agents/), Aalto Scientific Computing, CC-BY 4.0.

- "Before proposing a job, verify time, memory, CPUs, GPUs, and partition against the Triton documentation"
- "Ask before submitting or cancelling jobs, deleting files, or changing permissions."
- "Do not submit large numbers of small jobs individually. Group short tasks or use Slurm arrays"
- "Do not poll the queue aggressively. Wait at least 15 seconds between squeue/sacct calls, and stop watchers when they are no longer needed"
- "Keep computation data out of $HOME."
- "Save work frequently. Do not rely on long unsupervised sessions on the login node."

In FragPlace the human's approval of the plan is the ask before submitting: code submits only what the approved rules allow, and nothing is ever cancelled by an agent.

## 3. The decision table

Measured: about 1.5 s per MACE-MP-small force call on 146 atoms with 2 CPUs; the time scales with the atoms. Every threshold below is inferred from that measurement.

| Work of one heavy call | Expected time, inferred | Lane and resources |
|---|---|---|
| Any import of a potential or any force call | | never the login node |
| Up to 200 single points | under 10 min | the worker, or a step of a held allocation |
| 1 to 10 relaxations of 60 to 200 atoms | up to 70 min | the worker |
| 10 to 200 relaxations | 0.3 to 23 h | one sbatch job of 8 to 16 CPUs, a checkpoint per structure |
| Chunks of 30 min or more with the same resources; DFT; more than 200 structures | | an array of chunks; "a good target time for the array jobs would be approximately 30 minutes", from [Triton: array jobs](https://scicomp.aalto.fi/triton/tut/array/) |
| A GPU | | only when one stays busy for 30 min or more; the `.venv`'s torch is CPU only, so no GPU rule for now |

Read the estimate of `compute_plan` against this table, then set each rule: `auto` with `batch_above_min` where a step may be small or large, `worker` where it is always short, `batch` where it is always long.

## 4. The held allocation

Adapted, with attribution, from the MIT-licensed [euler-hpc plugin](https://github.com/jjans5/euler-hpc): one allocation for a session instead of a job per call.

1. The human runs `salloc --no-shell` with the time, memory and cores, and passes the job id as `FRAGPLACE_SLURM_JOB`.
2. Each heavy call runs as a step of it: `srun --jobid=<id> --overlap -n1 -c K --mem=M`.
3. Time left: `squeue -h -j <id> -o %L`.
4. Renew before it ends: the human holds a new allocation; an agent never does.

## 5. Storage and network

| Place | Rule |
|---|---|
| `/tmp` | node-local and wiped after your last job on a node; never a study, an environment or a model cache |
| `/scratch` or `$WRKDIR` | studies, the `.venv` and model caches |
| `$HOME` | small: measured at 93 % of 20 GB on 22 October 2026; MACE models download into `~/.cache` by default, so point the cache to `/scratch` |
| Network | the interactive node pht4 reached GitHub and Hugging Face in a check on 22 October 2026; Triton's documentation says other nodes may have no outside network, so download every model before a batch job starts |

## 6. Monitoring

| Question | Command |
|---|---|
| My jobs now | `slurm q` |
| My recent jobs | `slurm history` |
| How well a finished job used its CPUs and memory | `seff <job>` |
| State, exit code and time of a job | `sacct -j <job>` |
| GPU efficiency | `module load seff-gpu; seff <job>` |

Wait at least 15 seconds between two queue queries. A job missing from `squeue` has ended, not succeeded: "A job disappearing from the active queue does not prove success", from the Apache-2.0 pbs-hpc skill of [ChemGraph](https://github.com/argonne-lcf/ChemGraph). Read its state in `sacct`.

## 7. Ideas taken from wfl and ExPyRe

libAtoms wfl and ExPyRe are GPL-2.0, and wfl pins numpy below 2, so FragPlace takes their ideas only and none of their code.

- Few jobs, many structures in each.
- A pool inside each job, sized to its cores.
- The potential loaded once per worker, not once per structure.
- A job found again by the hash of its work, never submitted twice.
- The queue polled once per interval, no more often.

## 8. What FragPlace does by itself

| Lane | Where a heavy call runs |
|---|---|
| local | in the server's own process; inside a Slurm job, and on a machine without Slurm |
| worker | one long-lived worker job per session on a compute node, started by the plugin on the first heavy call; the potential stays loaded between calls |
| batch | one sbatch job per heavy call, with a pool of `workers` processes for the relaxations |
| auto | the worker, and batch when the estimate passes the rule's `batch_above_min` |

| Event | What code does |
|---|---|
| A rule's lane is batch, or auto above its threshold | submits one sbatch job, records it in `runs/<study>/jobs.json` |
| The same call again | finds the job by its hash and reattaches; no second submission |
| Polling | no more often than every 15 s |
| TIMEOUT | resubmits with twice the time |
| OUT_OF_MEMORY | resubmits with twice the memory |
| NODE_FAIL, PREEMPTED | resubmits as it was |
| A third failed attempt | stops; the call answers with an error carrying the Slurm state and the log tail, for the hpc-specialist and then the human |
| Cancelling | never; no `scancel` anywhere |

## 9. Procedure

1. At step 1\*, call `compute_plan` with the study and no rules; read the minutes per item and the totals.
2. Place each heavy step in the table of section 3; check its time, memory, cores and partition against section 1.
3. Call `compute_plan` with one rule per heavy tool and a reason; leave the rules with `note`. The human approves them with the plan; after that box they cannot change.
4. On an error with a Slurm state, read `sacct -j`, `seff` and `scontrol show job`, name the cause, and propose one change for the human.

Tools: `compute_plan`.
