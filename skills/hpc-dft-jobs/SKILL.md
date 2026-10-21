---
name: hpc-dft-jobs
description: Submitting DFT single points to a queue, what custodian handles by itself, and what to escalate; only with a DFT code and compute. Use when dft_single_points is called.
---

# DFT jobs on HPC

1. Check the settings of every job against `PROJECT.md` before submission; a mismatch is check 8 and stops the job.
2. Submit through `finalstate.compute.slurm`; the job script wraps the DFT command in custodian handlers, so SCF failures, POTIM and unconverged runs are retried by code.
3. The dft-recovery-agent reads a failure only after custodian gave up: the error, the handler that fired, the attempts in the job tracker.
4. Adjust one thing at a time, resubmit, and log the diagnosis in the trace; the tracker caps attempts at three and the human gets the job after that.
5. Never change a locked setting to make a job converge.

Tools: `dft_single_points`.
