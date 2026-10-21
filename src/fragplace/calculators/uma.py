"""UMA through fairchem. Weights are gated on Hugging Face under the FAIR Chemistry License; set HF_TOKEN."""
from __future__ import annotations

from . import ASEAdapter, register


@register("uma-s-1p2p1")
@register("uma-m-1p1")
class UMA(ASEAdapter):
    name = "uma"

    def __init__(self, model: str = "uma-s-1p2p1", task: str = "oc20", device: str = "cuda", **_):
        try:
            from fairchem.core import FAIRChemCalculator, pretrained_mlip
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install fairchem-core; UMA weights need a Hugging Face token") from e
        self.model = model
        self._calc = FAIRChemCalculator(pretrained_mlip.get_predict_unit(model, device=device), task_name=task)
