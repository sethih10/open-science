"""Published values with their sources; the literature-reader's tools and the source adapters behind them. Tools: literature_lookup. Defined in fragplace.registry."""
from __future__ import annotations

import json
import re
import urllib.request
from typing import List, Tuple

from ..runtime.journal import log, traced
from ..schemas.records import LiteratureValue

QUANTITIES = ("E_ads", "bond_length_d", "site")
MAX_VALUES = 2
SYSTEM = re.compile(r"^\s*([A-Z][a-z]?\w*)\((\w+)\)\s+(\S+)\s*$")    # "Pt(111) OH": metal, facet, adsorbate


@traced(step="prompt", tool="literature_lookup")
def literature_lookup(system: str, quantity: str, sources: List[str]) -> List[LiteratureValue]:
    """Published E_ads values with functional and site, and the length d of the bond to break, for a human to verify; one or two values, never from the model's memory.

    Board steps: prompt, 3.2. Status: core. Lane: laptop. Allowed roles: literature-reader.

    Inputs:
        system: str, metal, facet, adsorbate
        quantity: E_ads | bond_length_d | site
        sources: list of source names
    Outputs:
        values: list[LiteratureValue], verified_by_human False until the checkpoint
    Checks:
        - every value carries a DOI or URL
        - at most two values per quantity
    Thresholds:
        none
    Wraps:
        - paper-qa2 for papers
        - Materials Project API through the LLaMP pattern
        - Catalysis-Hub
    Logs: query; every value with its source.

    system reads "Pt(111) OH". Sources are asked in order and the first two values with a source are kept; a
    source that fails is logged and the next one asked; when none answers the call fails with every reason.
    """
    if quantity not in QUANTITIES:
        raise ValueError(f"quantity {quantity!r}; known: {', '.join(QUANTITIES)}")
    unknown = [s for s in sources if s not in SOURCES]
    if unknown:
        raise ValueError(f"unknown sources {unknown}; known: {', '.join(SOURCES)}")
    log("literature_lookup", f"query {quantity} of {system} from {', '.join(sources)}")
    values, errors = [], []
    for name in sources:
        try:
            values += [v for v in SOURCES[name]().lookup(system, quantity) if v.source]
        except Exception as e:  # noqa: BLE001 - one source down is not a failed lookup
            errors.append(f"{name}: {type(e).__name__}: {e}")
            log("literature_lookup", f"{name} gave nothing: {type(e).__name__}: {e}")
        if len(values) >= MAX_VALUES:
            break
    values = values[:MAX_VALUES]
    if not values:
        raise LookupError("no source gave a value: " + ("; ".join(errors) or "no match"))
    for v in values:
        log("literature_lookup", f"{v.quantity} {v.value} {v.unit}, {v.functional}, site {v.site}: {v.source}")
    return values


def parse_system(system: str) -> Tuple[str, str, str]:
    m = SYSTEM.match(system)
    if not m:
        raise ValueError(f"system {system!r}; write it as metal(facet) adsorbate, such as Pt(111) OH")
    return m.group(1), m.group(2), m.group(3)


# ---- source adapters, each returning LiteratureValue records with a DOI or URL; the LLM never cites from memory
class MaterialsProject:
    name = "materials_project"

    def lookup(self, system: str, quantity: str):
        try:
            from mp_api.client import MPRester  # noqa: F401
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install mp-api; set MP_API_KEY") from e
        raise NotImplementedError("Materials Project holds bulk and surface properties; it serves none of E_ads, bond_length_d or site")


class CatalysisHub:
    """Reaction energies of adsorption, with functional, site and publication, from the public GraphQL API."""
    name = "catalysis_hub"
    url = "https://api-catalysis-hub.slac.stanford.edu/graphql"   # api.catalysis-hub.org redirects here
    timeout_s = 20
    query = ('{ reactions(first: 20, surfaceComposition: "%s", facet: "%s", products: "~%sstar") { edges { node { '
             'Equation reactionEnergy surfaceComposition facet sites dftFunctional products pubId } } } }')

    def lookup(self, system: str, quantity: str):
        if quantity == "bond_length_d":
            raise NotImplementedError("Catalysis-Hub holds reaction energies, not bond lengths; d comes from the structures")
        metal, facet, ads = parse_system(system)
        data = self.post(self.query % (metal, facet, ads))
        out = []
        for edge in data.get("data", {}).get("reactions", {}).get("edges", []):
            node = edge.get("node") or {}
            if node.get("reactionEnergy") is None or not node.get("pubId"):
                continue
            products = json.loads(node["products"]) if isinstance(node.get("products"), str) else (node.get("products") or {})
            if set(products) != {f"{ads}star"}:
                continue
            sites = json.loads(node["sites"]) if isinstance(node.get("sites"), str) else (node.get("sites") or {})
            out.append(LiteratureValue(quantity="E_ads", value=float(node["reactionEnergy"]), unit="eV", system=system,     # a site comes with its energy
                                       functional=node.get("dftFunctional"), site=str(sites.get(ads, sites)) if sites else None,
                                       source=f"https://www.catalysis-hub.org/publications/{node['pubId']}"))
        return out

    def post(self, query: str) -> dict:
        req = urllib.request.Request(self.url, data=json.dumps({"query": query}).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout_s) as r:
            return json.loads(r.read().decode())


class Papers:
    name = "papers"

    def lookup(self, system: str, quantity: str):
        try:
            import paperqa  # noqa: F401
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install paper-qa") from e
        raise NotImplementedError("paper-qa answers in prose; turning an answer into values with one citation each is not built")


SOURCES = {"materials_project": MaterialsProject, "catalysis_hub": CatalysisHub, "papers": Papers}
