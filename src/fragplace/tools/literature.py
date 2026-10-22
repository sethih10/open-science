"""Published values with their sources; the literature-reader's tools and the source adapters behind them. Tools: literature_lookup. Defined in fragplace.registry."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

from ..runtime.journal import log, traced
from ..schemas.records import LiteratureValue

QUANTITIES = ("E_ads", "reaction_energy", "bond_length_d", "site")
MAX_VALUES = 2
SYSTEM = re.compile(r"^\s*([A-Z][a-z]?\w*)\((\w+)\)\s+(\S+)\s*$")    # "Pt(111) OH", or "Pt(111) OH->O+H" for a reaction
REACTION = re.compile(r"^(\w+)->(\w+)\+(\w+)$")
CITATION = re.compile(r"^(https?://\S+|10\.\d{4,9}/\S+|doi:\s*10\.\S+)$", re.I)


@traced(step="prompt", tool="literature_lookup")
def literature_lookup(system: str, quantity: str, sources: List[str], reported: Optional[List[LiteratureValue]] = None) -> List[LiteratureValue]:
    """Published E_ads values with functional and site, the reaction energy of AB* -> A* + B*, and the length d of the bond to break, for a human to verify; one or two values, never from the model's memory.

    Board steps: prompt, 3.2. Status: core. Lane: laptop. Allowed roles: literature-reader.

    Inputs:
        system: str, surface(facet) species, or surface(facet) AB->A+B for a reaction
        quantity: E_ads | reaction_energy | bond_length_d | site
        sources: list of source names
        reported: values the literature-reader read in papers, each with its DOI or URL; source papers
    Outputs:
        values: list[LiteratureValue], verified_by_human False until the checkpoint
    Checks:
        - every value carries a DOI or URL
        - at most two values per quantity
    Thresholds:
        none
    Wraps:
        - papers: values the literature-reader read in papers it found by web search
        - CMR CatApp, DTU's open database of reaction energies
        - Catalysis-Hub, with a personal API key
        - Materials Project API through the LLaMP pattern
    Logs: query; every value with its source.

    system reads "Pt(111) OH", or "Pt(111) OH->O+H" for the reaction energy of AB* -> A* + B*. Sources are asked
    in order and the first two values with a source are kept; a source that fails is logged and the next one
    asked; when none answers the call fails with every reason. The papers source holds what the
    literature-reader passes as reported: a value without a DOI or URL fails the call before any source is asked,
    a value that names another system is not this query's, and every value stays unverified until the human
    checks it against its source.
    """
    if quantity not in QUANTITIES:
        raise ValueError(f"quantity {quantity!r}; known: {', '.join(QUANTITIES)}")
    unknown = [s for s in sources if s not in SOURCES]
    if unknown:
        raise ValueError(f"unknown sources {unknown}; known: {', '.join(SOURCES)}")
    if reported and "papers" not in sources:
        raise ValueError("reported values come from papers: name the source papers")
    papers = Papers(reported or [])          # outside the loop: an uncited value is the caller's error, not a source down
    log("literature_lookup", f"query {quantity} of {system} from {', '.join(sources)}")
    values, errors = [], []
    for name in sources:
        try:
            adapter = papers if name == "papers" else SOURCES[name]()
            values += [v for v in adapter.lookup(system, quantity) if v.source]
        except Exception as e:  # noqa: BLE001 - one source down is not a failed lookup
            errors.append(f"{name}: {type(e).__name__}: {e}")
            log("literature_lookup", f"{name} gave nothing: {type(e).__name__}: {e}")
        if len(values) >= MAX_VALUES:
            break
    values = [v.model_copy(update={"verified_by_human": False}) for v in values[:MAX_VALUES]]
    if not values:
        raise LookupError("no source gave a value: " + ("; ".join(errors) or "no match"))
    for v in values:
        log("literature_lookup", f"{v.quantity} {v.value} {v.unit}, {v.functional}, site {v.site}: {v.source}")
    return values


def parse_system(system: str) -> Tuple[str, str, str]:
    m = SYSTEM.match(system)
    if not m:
        raise ValueError(f"system {system!r}; write it as surface(facet) species, such as Pt(111) OH or NaCl(100) H2O")
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
    """Reaction energies of adsorption, with functional, site and publication, from the GraphQL API. The API asks for
    a free personal key since 2026, from an ORCID sign-in; it is read from CATHUB_API_KEY, the official client's
    variable, and never written to a record."""
    name = "catalysis_hub"
    url = "https://api-catalysis-hub.slac.stanford.edu/graphql"   # the bare https://api.catalysis-hub.org/ redirects here
    key_page = "https://api-catalysis-hub.slac.stanford.edu/auth/login"
    timeout_s = 20
    query = ('{ reactions(first: 20, surfaceComposition: "%s", facet: "%s", products: "~%sstar") { edges { node { '
             'Equation reactionEnergy surfaceComposition facet sites dftCode dftFunctional products pubId publication { doi } } } } }')

    def lookup(self, system: str, quantity: str):
        if quantity != "E_ads":
            raise NotImplementedError(f"Catalysis-Hub is asked here for E_ads only, not {quantity}")
        metal, facet, ads = parse_system(system)
        data = self.post(self.query % (metal, facet, ads))
        out = []
        for edge in ((data.get("data") or {}).get("reactions") or {}).get("edges", []):
            node = edge.get("node") or {}
            if node.get("reactionEnergy") is None or not node.get("pubId"):
                continue
            products = json.loads(node["products"]) if isinstance(node.get("products"), str) else (node.get("products") or {})
            if set(products) != {f"{ads}star"}:
                continue
            sites = json.loads(node["sites"]) if isinstance(node.get("sites"), str) else (node.get("sites") or {})
            doi = (node.get("publication") or {}).get("doi")
            out.append(LiteratureValue(quantity="E_ads", value=float(node["reactionEnergy"]), unit="eV", system=system,     # a site comes with its energy
                                       functional=" ".join(x for x in (node.get("dftCode"), node.get("dftFunctional")) if x) or None,
                                       site=str(sites.get(ads, sites)) if sites else None,
                                       source=f"https://doi.org/{doi}" if doi else f"https://www.catalysis-hub.org/publications/{node['pubId']}"))
        return out

    def post(self, query: str) -> dict:
        key = os.environ.get("CATHUB_API_KEY")
        if not key:
            raise PermissionError(f"not configured: Catalysis-Hub needs a free personal API key; sign in with ORCID at {self.key_page} "
                                  "and set CATHUB_API_KEY")
        req = urllib.request.Request(self.url, data=json.dumps({"query": query}).encode(),
                                     headers={"Content-Type": "application/json", "Accept": "application/json", "X-API-Key": key})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as r:
                data = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            error = PermissionError if e.code in (401, 403) else ConnectionError
            raise error(f"Catalysis-Hub answered {e.code}: {_server_message(e)}") from None
        if data.get("errors") and not (data.get("data") or {}).get("reactions"):     # GraphQL may answer errors beside an empty data
            raise LookupError("Catalysis-Hub: " + "; ".join(str(x.get("message", x)) if isinstance(x, dict) else str(x) for x in data["errors"]))
        return data


def _server_message(e: "urllib.error.HTTPError") -> str:
    """The server's own explanation, which urllib leaves in the body: 'Missing API key ...' rather than 'UNAUTHORIZED'.
    GraphQL puts it under errors, a REST layer under message, error or detail; any other body is quoted as text."""
    try:
        raw = e.read().decode(errors="replace")
    except OSError:
        return str(e.reason)
    try:
        body = json.loads(raw)
    except ValueError:
        return " ".join(raw.split())[:300] or str(e.reason)
    if isinstance(body, dict):
        errors = body.get("errors")
        if isinstance(errors, list) and errors:
            return "; ".join(str(x.get("message", x)) if isinstance(x, dict) else str(x) for x in errors)
        for key in ("message", "error", "detail"):
            if body.get(key):
                return str(body[key])
    return str(e.reason)


class CMRCatApp:
    """CMR CatApp, DTU's open ASE database of reaction energies AB* -> A* + B* on surfaces, with functional and
    reference: https://cmr.fysik.dtu.dk/catapp/catapp.html. Downloaded once into FRAGPLACE_DATA, the user's cache
    by default; no key. It holds reaction energies and barriers, no adsorption energies and no bond lengths."""
    name = "cmr_catapp"
    url = "https://wiki.fysik.dtu.dk/cmr-files/catapp.db"
    page = "https://cmr.fysik.dtu.dk/catapp/catapp.html"
    timeout_s = 60

    def path(self) -> Path:
        return Path(os.environ.get("FRAGPLACE_DATA") or Path.home() / ".cache" / "fragplace") / "catapp.db"

    def database(self):
        from ase.db import connect
        path = self.path()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(self.url, timeout=self.timeout_s) as r:
                data = r.read()
            if not data.startswith(b"SQLite format 3\x00"):        # a page in place of the database would poison the cache
                raise LookupError(f"CMR CatApp: {self.url} gave no SQLite database; download it by hand from {self.page} to {path}")
            partial = path.with_suffix(".part")
            partial.write_bytes(data)
            partial.rename(path)
            log("literature_lookup", f"CMR CatApp downloaded once from {self.url} to {path}")
        return connect(str(path))

    def lookup(self, system: str, quantity: str):
        if quantity != "reaction_energy":
            raise NotImplementedError(f"CMR CatApp holds reaction energies AB* -> A* + B*, not {quantity}")
        surface, facet, reaction = parse_system(system)
        m = REACTION.match(reaction)
        if not m:
            raise ValueError(f"a reaction reads AB->A+B, such as OH->O+H; got {reaction!r}")
        ab, a, b = m.groups()
        out = []
        for row in self.database().select(ab=f"{ab}*", surface=f"{surface}({facet})"):
            if {row.get("a"), row.get("b")} != {f"{a}*", f"{b}*"} or row.get("er") is None:
                continue
            out.append(LiteratureValue(quantity="reaction_energy", value=float(row.er), unit="eV", system=system, functional=row.get("xc"),
                                       site=row.get("site"), source=row.get("url") or self.page))
        return out


class Papers:
    """Values the literature-reader read in papers it found by web search and passes in as reported. Each must cite
    a DOI or URL, checked when the source is made; a value answers a query of its quantity and of its own system,
    or of any system when it names none. The human checks each against its source before anything uses it."""
    name = "papers"

    def __init__(self, reported: List[LiteratureValue]):
        uncited = [v for v in reported if not CITATION.match(v.source.strip())]
        if uncited:
            raise ValueError("every reported value cites a DOI or a URL; not: " + "; ".join(
                f"{v.quantity} {v.value} {v.unit}, source {v.source!r}" for v in uncited))
        self.reported = reported

    def lookup(self, system: str, quantity: str):
        query = " ".join(system.split())
        return [v.model_copy(update={"system": v.system or system}) for v in self.reported
                if v.quantity == quantity and " ".join(v.system.split()) in ("", query)]


SOURCES = {"papers": Papers, "cmr_catapp": CMRCatApp, "catalysis_hub": CatalysisHub, "materials_project": MaterialsProject}
