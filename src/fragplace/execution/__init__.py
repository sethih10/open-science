"""Where a calculation runs. The laptop and GPU lanes use LocalBackend; DFT uses a queue.

A Backend submits a Job and returns a handle; the caller polls. Deterministic error handlers run before any
agent sees a failure: custodian for VASP, the equivalent for Quantum ESPRESSO.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Protocol


@dataclass
class Job:
    name: str
    command: str
    workdir: str
    resources: Dict[str, str] = field(default_factory=dict)   # nodes, time, partition, gpus


@dataclass
class JobHandle:
    id: str
    backend: str
    state: str = "submitted"            # submitted | running | done | failed


class Backend(Protocol):
    name: str

    def submit(self, job: Job) -> JobHandle: ...
    def status(self, handle: JobHandle) -> str: ...
    def result_dir(self, handle: JobHandle) -> str: ...


def get(name: str) -> Backend:
    if name == "local":
        from .local import LocalBackend
        return LocalBackend()
    if name == "slurm":
        from .slurm import SlurmBackend
        return SlurmBackend()
    raise KeyError(f"unknown backend {name}; known: local, slurm")
