"""The relaxation pool: several relaxations at once in worker processes, for the heavy cost of a study.

A pool has N worker processes, started with spawn: a fork after torch has started its threads can hang. Each worker
sets the OpenMP and torch threads to its share of the CPUs, cpus // N, and builds its calculator once through
fragplace.calculators.get, which keeps one per process. Workers only relax: atoms in; positions, energy, steps,
fmax and convergence out, and the optimiser's trajectory at the path the parent names. The parent keeps every
structure file, cache entry and trace line, so the trace keeps one writer, and takes the answers in the order of
the candidates, so the results are the serial path's in the same order.

relaxation() uses the pool when workers() is above 1: the approved rule's workers, which the study sets around its
call with using(), else FRAGPLACE_WORKERS.
"""
from __future__ import annotations

import multiprocessing
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, Iterator, Mapping, Optional, Sequence, Tuple

from .. import calculators
from .local import BLAS_THREADS_MAX, cpu_budget

ENV = "FRAGPLACE_WORKERS"
START_METHOD = "spawn"          # never fork, see the module docstring; forkserver would do as well
_CHOSEN: ContextVar[Optional[int]] = ContextVar("fragplace_pool_workers", default=None)
_THREADS = 1                    # in a worker process: its share of the CPUs, set when it starts


def workers(env: Optional[Mapping[str, str]] = None) -> int:
    """The processes of the relaxation pool: the approved rule's when using() set them, else FRAGPLACE_WORKERS, else 1."""
    chosen = _CHOSEN.get()
    if chosen is not None:
        return max(1, int(chosen))
    text = (os.environ if env is None else env).get(ENV, "").strip()
    return max(1, int(text)) if text else 1


@contextmanager
def using(n: Optional[int]) -> Iterator[None]:
    """workers() is n inside the block; None leaves it to FRAGPLACE_WORKERS."""
    token = _CHOSEN.set(n)
    try:
        yield
    finally:
        _CHOSEN.reset(token)


def shape(jobs: int, n: int, cpus: Optional[int] = None) -> Tuple[int, int]:
    """The pool for jobs relaxations asked to run on n processes: no more processes than jobs or CPUs, and the CPUs
    shared out evenly, at least one thread each. cpus is this process's budget unless given."""
    cpus = cpus or cpu_budget()
    procs = max(1, min(n, jobs, cpus))
    return procs, max(1, cpus // procs)


def relax_all(jobs: Sequence[Tuple[Any, Optional[str]]], calculator: str, fmax: float, steps: int, n: int,
              cpus: Optional[int] = None) -> Iterator[Dict[str, Any]]:
    """Relax each (atoms, trajectory path) of jobs in a pool of n processes; yields each answer in the order of jobs,
    as soon as it and every one before it are done. A worker's error is raised at its place in that order, and
    closing the iterator ends the pool, cancelling what has not started."""
    procs, threads = shape(len(jobs), n, cpus)
    pool = ProcessPoolExecutor(max_workers=procs, mp_context=multiprocessing.get_context(START_METHOD), initializer=_start,
                               initargs=(threads,))
    try:
        futures = [pool.submit(_relax, atoms.copy(), calculator, float(fmax), int(steps), trajectory) for atoms, trajectory in jobs]
        for f in futures:
            yield f.result()
    finally:
        pool.shutdown(wait=True, cancel_futures=True)


def _start(threads: int) -> None:
    """A worker's start: its share of the CPUs for every library that reads a thread count, before any of them loads."""
    global _THREADS
    _THREADS = threads
    os.environ.update(OMP_NUM_THREADS=str(threads), MKL_NUM_THREADS=str(threads), OPENBLAS_NUM_THREADS=str(min(threads, BLAS_THREADS_MAX)))


def _relax(atoms, calculator: str, fmax: float, steps: int, trajectory: Optional[str]) -> Dict[str, Any]:
    """One relaxation in a worker, with the calculator this process built on its first job."""
    adapter = calculators.get(calculator)
    torch = sys.modules.get("torch")
    if torch is not None and torch.get_num_threads() != _THREADS:
        torch.set_num_threads(_THREADS)
    relaxed, converged, n, fmax_reached = adapter.relax(atoms, fmax=fmax, steps=steps, trajectory=trajectory)
    return {"positions": relaxed.get_positions(), "energy_eV": float(relaxed.get_potential_energy()), "steps": int(n),
            "fmax_eV_per_A": float(fmax_reached), "converged": bool(converged)}
