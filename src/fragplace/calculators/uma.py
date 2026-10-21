"""UMA through fairchem. Weights are gated on Hugging Face under the FAIR Chemistry License; set HF_TOKEN."""
from __future__ import annotations

from . import register


@register("uma-s-1p2p1")
@register("uma-m-1p1")
class UMA:
    name = "uma"

    def __init__(self, model: str = "uma-s-1p2p1", task: str = "oc20", device: str = "cuda"):
        try:
            from fairchem.core import FAIRChemCalculator, pretrained_mlip
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install fairchem-core; UMA weights need a Hugging Face token") from e
        self.model = model
        self._calc = FAIRChemCalculator(pretrained_mlip.get_predict_unit(model, device=device), task_name=task)

    def energy_forces(self, atoms):
        atoms.calc = self._calc
        return atoms.get_potential_energy(), atoms.get_forces()

    def relax(self, atoms, fmax: float, steps: int):
        from ase.optimize import BFGS
        atoms.calc = self._calc
        opt = BFGS(atoms, logfile=None)
        converged = opt.run(fmax=fmax, steps=steps)
        return atoms, bool(converged), opt.get_number_of_steps()
