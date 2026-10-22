"""UMA through fairchem. Weights are gated on Hugging Face under the FAIR Chemistry License; set HF_TOKEN."""
from __future__ import annotations

from typing import Optional

from . import ASEAdapter, device, register


@register("uma-s-1p2p1")
@register("uma-m-1p1")
class UMA(ASEAdapter):
    name = "uma"

    def __init__(self, name: str = "uma-s-1p2p1", task: str = "oc20", device_name: Optional[str] = None, **_):
        try:
            from fairchem.core import FAIRChemCalculator, pretrained_mlip
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install fairchem-core; UMA weights need a Hugging Face token") from e
        self.name = self.model = name
        self._calc = FAIRChemCalculator(pretrained_mlip.get_predict_unit(name, device=device_name or device()), task_name=task)
