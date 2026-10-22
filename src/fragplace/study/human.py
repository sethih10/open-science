"""The human's side of a study in the chat: the question boxes the orchestrator shows, built by code from the
records, and the answers, recorded by code.

The orchestrator asks with Claude Code's question box, AskUserQuestion, exactly as these builders return it.
Claude Code then runs record() as a PostToolUse hook with the questions and the answers the human chose. A
question that names a study, written "[<study>] ...", is recorded in that study: the question and the answer go
to the trace under "human", word for word, and the header says what else the answer sets:

| Header | Question text after the study | What the answer records |
|---|---|---|
| Checkpoint | `<checkpoint>: ...` | the checkpoint passed, when the answer is Approve |
| Pick | `<checkpoint>: ...`, multi-select | the candidates kept at review flagged cases, or picked as final states |
| Verify | `approve settings: ...` or `bond length d: ...`, multi-select | the published values, lit:<index>, the human checked; at approve settings stored with Approve |
| Decision | `<tool>.<name>: ...` | the open decision set to the chosen value, before the lock |
| Interview | `<n>. ...` | the answer in row n of the Interview table of PROJECT.md |

The model never writes these records. Claude Code removes any answer the model puts in the tool call before the
human sees the question, so the answers here are the human's; runtime.policy's guard refuses such a call
outright. A question without a study, or with another header, is left alone, so the hook is safe in any
session. The approver is the human at the keyboard: FRAGPLACE_HUMAN, else git's user.name, else the login name.
"""
from __future__ import annotations

import getpass
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..errors import FragPlaceError
from ..registry.agents import CHECKPOINTS
from ..registry.tools import runs_dft
from ..runtime import project
from ..runtime.journal import default_root
from ..schemas.records import DescriptorCard, DoubtFlag, GateResult, LiteratureValue, RankedCandidate
from .store import Study, record_choice, record_decision, record_interview, record_verified
from .summary import benchmark_text, plan_rows, refresh_literature

QUESTION = re.compile(r"^\[(?P<study>[A-Za-z0-9][\w.-]*)\]\s*(?P<rest>.+)$", re.S)
CANDIDATE = re.compile(r"\bA\d{3}-B\d{3}(?:o\d+)?\b")
LITERATURE = re.compile(r"\blit:\d+\b")
APPROVE, KEEP_ALL = "Approve", "Keep all"
PER_QUESTION, PER_BOX = 4, 4          # the question box's limits: options per question, questions per box
INTERVIEW_ROWS = 5


# ---- the questions
def _approve(study: str, checkpoint: str, question: str, preview: str, approve: str) -> Dict[str, Any]:
    options = [{"label": APPROVE, "description": approve, "preview": preview},
               {"label": "Change something", "description": "Say what to change in the note or under Other; nothing is recorded as passed",
                "preview": preview},
               {"label": "Stop here", "description": "Leave the study where it is; it resumes from this point later", "preview": preview}]
    return {"question": f"[{study}] {checkpoint}: {question}", "header": "Checkpoint", "multiSelect": False, "options": options}


def _picks(study: str, checkpoint: str, question: str, items: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Multi-select questions over candidates, at most four per question and four questions per box."""
    chunks = [items[k:k + PER_QUESTION] for k in range(0, min(len(items), PER_QUESTION * PER_BOX), PER_QUESTION)]
    out = []
    for n, chunk in enumerate(chunks):
        if len(chunk) == 1:
            chunk = chunk + [{"label": "None of these", "description": "Choose nothing from this group"}]
        part = f", {n + 1} of {len(chunks)}" if len(chunks) > 1 else ""
        out.append({"question": f"[{study}] {checkpoint}: {question}{part}", "header": "Pick", "multiSelect": True, "options": chunk})
    return out


def checkpoint_box(c: Study, checkpoint: str) -> Dict[str, Any]:
    """The question box for a due checkpoint, ready for AskUserQuestion, with what the human looks at in the preview."""
    s = c.settings(locked=False)
    study = c.run.study
    if checkpoint == "approve settings":
        dft = runs_dft(s.protocol)
        rows = [("System", f"{s.adsorbate}* → {s.product[0]}* + {s.product[1]}* on {s.metal}({s.facet})"),
                ("Protocol", f"{s.protocol}: {s.protocol_reason}")]
        if dft:
            rows += [("Functional", f"{s.functional}, dispersion {s.dispersion or 'none'}"),
                     ("Pseudopotentials, cutoff", f"{s.pseudopotential_family}, {s.cutoff_eV} eV"), ("k-mesh", str(s.kmesh))]
        rows += [("Cell", f"{s.cell_repeat} repeat of the supplied slab"), ("Force threshold", f"{s.force_threshold_eV_per_A} eV/Å"),
                 ("Gas references", ", ".join(f"{g.species} {g.energy_eV:.4f} eV" for g in s.gas_references) or "none" if dft else
                  ", ".join(s.decisions.get("calculation_protocol.gas_references") or []) + ", computed with the potential chosen at 1*"),
                 ("Potentials to benchmark", str(project.decision("mlip_selection", "candidates", s))),
                 ("Decisions set", f"{len(s.decisions)}; missing {', '.join(project.missing_decisions(s)) or 'none'}"),
                 ("Energies from", "the potential chosen at 1*; these settings are the reference level of theory, used by DFT only through "
                                   "dft_single_points, not built yet" if dft else "no DFT runs in this study; the potential chosen at 1* computes every energy")]
        box = [_approve(study, checkpoint, "lock these settings for the whole study?", _table(rows),
                        "Lock PROJECT.md as shown; a later change means a new study")]
        lit = c.many("literature", LiteratureValue)
        items = [{"label": f"lit:{k}", "description": f"{v.quantity} {v.value} {v.unit}, {v.functional or 'functional not given'}, "
                                                    f"site {v.site or 'not given'}: {v.source}"} for k, v in enumerate(lit)]
        box += [dict(q, header="Verify") for q in _picks(study, checkpoint, "which published values did you check against their source?", items)][:PER_BOX - 1]
    elif checkpoint == "approve the plan":
        m = c.data.get("mlip", {})
        rows = [("Potential", f"{m.get('calculator')}: {m.get('reason')}"), ("Committee", ", ".join(m.get("committee_used", [])))]
        rows += [(k, benchmark_text(v)) for k, v in m.get("benchmark", {}).items()]
        rows += plan_rows(c.data)
        rows += [("Next", "sites, pairs in the window, B placed, pull-force screen, ordering, relaxation, gate, clustering, doubt")]
        box = [_approve(study, checkpoint, "run the plan with this potential?", _table(rows), "Go on to sites, pairs and relaxation with this potential")]
    elif checkpoint == "review flagged cases":
        flags = c.many("flags", DoubtFlag)
        gates = c.many("gates", GateResult)
        rows = [("Gate", f"{sum(g.passed for g in gates)} of {len(gates)} passed"), ("Kept after clustering", ", ".join(c.data.get("kept", [])))]
        rows += [(f.candidate_id, f"{f.trigger}, spread {f.committee_spread_eV:.3f} eV" + (", escalated" if f.escalate else "")) for f in flags]
        box = [_approve(study, checkpoint, "keep every kept candidate for the ranking?", _table(rows),
                        "Keep them all; to drop some, choose Change something and say which")]
    elif checkpoint == "pick up to five final states":
        cards = {x.candidate_id: x for x in c.many("cards_kept", DescriptorCard)}
        items = []
        for r in c.many("ranked", RankedCandidate):
            card = cards.get(r.candidate_id)
            dist = f"A–B {card.AB_distance_A:.2f} Å, shell {card.site_graph_distance}" if card and card.AB_distance_A is not None else ""
            items.append({"label": r.candidate_id, "description": f"rank {r.rank}; {dist}; E {r.energy_eV:.3f} eV"
                                                                  + (f"; doubt {r.doubt.trigger}" if r.doubt else "")})
        limit = project.decision("ranking", "shortlist_size", s)
        box = _picks(study, checkpoint, f"which final states do you pick, at most {limit}?", items) if items else [
            _approve(study, checkpoint, "no candidate survived the gate; close the pick with none and write the report?",
                     _table([("Ranked", "none"), ("Rejected", "every candidate; the report lists each with its reason")]),
                     "Pick nothing; the report records the rejections and the recombination rate")]
    elif checkpoint == "interpret results":
        r = c.data.get("report", {})
        rows = [("Report", str(c.run.dir / "report.md")), ("Final states", str(len(r.get("final_states", [])))),
                ("Rejected", str(len(r.get("rejected", [])))), ("Recombination rate, nearest shell", str(r.get("recombination_rate")))]
        box = [_approve(study, checkpoint, "accept the report as the record of this study?", _table(rows),
                        "Close the study; put your interpretation in the note")]
    else:
        raise FragPlaceError(f"no checkpoint {checkpoint!r}; known: {', '.join(CHECKPOINTS)}")
    return {"questions": box}


def verify_box(c: Study, quantity: str = "bond_length_d") -> Dict[str, Any]:
    """The question box for published values found outside a checkpoint, such as d at 3.2: which did the human check?"""
    lit = c.many("literature", LiteratureValue)
    items = [{"label": f"lit:{k}", "description": f"{v.system}: {v.value} {v.unit}, {v.functional or 'functional not given'}: {v.source}"}
             for k, v in enumerate(lit) if v.quantity == quantity and not v.verified_by_human]
    name = {"bond_length_d": "bond length d"}.get(quantity, quantity)
    return {"questions": [dict(q, header="Verify") for q in _picks(c.run.study, name, "which of these did you check against the source?", items)]}


def interview_boxes(c: Study) -> List[Dict[str, Any]]:
    """The interview questions of PROJECT.md still unanswered, one row each. The orchestrator adds two to four likely
    answers to each, drafted by the computational-chemist; the human picks one or writes under Other."""
    rows = _interview_rows(c.run.dir / "PROJECT.md")
    qs = [{"question": f"[{c.run.study}] {n}. {q}", "header": "Interview", "multiSelect": False, "options": []}
          for n, (q, answer) in enumerate(rows, 1) if not answer]
    return [{"questions": qs[k:k + PER_BOX]} for k in range(0, len(qs), PER_BOX)]


def decision_question(study: str, key: str, meaning: str) -> Dict[str, Any]:
    """One open decision; the orchestrator adds two to four values from the docs, each with where it comes from."""
    return {"question": f"[{study}] {key}: {meaning}", "header": "Decision", "multiSelect": False, "options": []}


def _table(rows: List[tuple]) -> str:
    return "| | |\n|---|---|\n" + "\n".join(f"| {k} | {str(v).replace('|', '/')} |" for k, v in rows)


def _interview_rows(path: Path) -> List[tuple]:
    text = path.read_text() if path.exists() else ""
    section = text.split("## Interview", 1)[1].split("\n## ", 1)[0] if "## Interview" in text else ""
    rows = [line for line in section.splitlines() if line.startswith("|") and not line.startswith("|---")][1:]
    return [tuple(cell.strip() for cell in line.strip().strip("|").split("|", 1)) for line in rows][:INTERVIEW_ROWS]


# ---- the answers
@dataclass
class Answer:
    study: str
    header: str
    rest: str
    question: str
    answer: str
    notes: str = ""
    descriptions: Dict[str, str] = field(default_factory=dict)

    @property
    def labels(self) -> List[str]:
        return [x.strip() for x in self.answer.split(",") if x.strip()]

    def checkpoint(self) -> Optional[str]:
        name = self.rest.split(":", 1)[0].strip().lower()
        return next((c for c in CHECKPOINTS if c == name), None)

    def reason(self) -> str:
        said = "; ".join(f"{x}: {self.descriptions[x]}" if self.descriptions.get(x) else x for x in self.labels) or self.answer
        return f"{said}; note: {self.notes}" if self.notes else said


def human_name(cwd: Optional[str] = None) -> str:
    """Who is answering: FRAGPLACE_HUMAN, else git's user.name where Claude Code runs, else the login name."""
    if os.environ.get("FRAGPLACE_HUMAN"):
        return os.environ["FRAGPLACE_HUMAN"]
    try:
        name = subprocess.run(["git", "config", "user.name"], cwd=cwd or None, capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        name = ""
    return name or getpass.getuser()


def parse(payload: Dict[str, Any]) -> List[Answer]:
    """The questions of one question box that name a study, each with the answer Claude Code collected."""
    tool_input = payload.get("tool_input") or {}
    response = payload.get("tool_response")
    answers = (response.get("answers") if isinstance(response, dict) else None) or tool_input.get("answers") or {}
    notes = (response.get("annotations") if isinstance(response, dict) else None) or tool_input.get("annotations") or {}
    out = []
    for q in tool_input.get("questions") or []:
        text = str(q.get("question", ""))
        m = QUESTION.match(text.strip())
        if not m or text not in answers:
            continue
        given = answers[text]
        given = ", ".join(map(str, given)) if isinstance(given, list) else str(given)
        note = notes.get(text, {}) if isinstance(notes, dict) else {}
        out.append(Answer(study=m["study"], header=str(q.get("header", "")).strip().lower(), rest=m["rest"].strip(), question=text,
                          answer=given.strip(), notes=str(note.get("notes", "") if isinstance(note, dict) else note).strip(),
                          descriptions={str(o.get("label", "")): str(o.get("description", "")) for o in q.get("options") or []}))
    return out


def record(payload: Dict[str, Any], root: Optional[Path] = None) -> List[str]:
    """Record every study question of one question box; returns one line per record, for the model to read."""
    root = Path(root or default_root())
    who = human_name(payload.get("cwd"))
    said: List[str] = []
    every = parse(payload)
    answers = [a for a in every if (root / "runs" / a.study).is_dir()]
    said += [f"[{a.study}] no such study under {root / 'runs'}; nothing recorded" for a in every if a not in answers]
    for a in answers:
        Study(root, a.study).run.event("chat", "AskUserQuestion", "human", {"question": a.question, "answer": a.answer}, "",
                                       message=f"{who} answered '{a.question}': {a.answer}" + (f"; note: {a.notes}" if a.notes else ""))
    pending: Dict[tuple, Dict[str, Any]] = {}
    for a in answers:
        try:
            if a.header == "decision":
                key = a.rest.split(":", 1)[0].strip()
                record_decision(root, a.study, key, _value(a.answer), who, a.reason())
                said.append(f"[{a.study}] decision {key} = {_value(a.answer)!r}, set by {who}")
            elif a.header == "interview":
                n = int(re.match(r"\D*(\d+)", a.rest).group(1))
                record_interview(root, a.study, n, a.answer + (f"; {a.notes}" if a.notes else ""), who)
                said.append(f"[{a.study}] interview answer {n} written to PROJECT.md")
            elif a.header == "verify" and a.checkpoint() is None:
                marked = record_verified(root, a.study, LITERATURE.findall(a.answer), who) if LITERATURE.search(a.answer) else []
                said.append(f"[{a.study}] checked against the source: {', '.join(marked)}" if marked else f"[{a.study}] no published value checked")
                if marked:
                    refresh_literature(Study(root, a.study))
            elif a.header in ("checkpoint", "pick", "verify"):
                cp = a.checkpoint()
                if cp is None:
                    said.append(f"[{a.study}] '{a.rest}' names no checkpoint; known: {', '.join(CHECKPOINTS)}")
                    continue
                slot = pending.setdefault((a.study, cp), {"approve": False, "pick": False, "chosen": [], "reasons": []})
                if a.header == "checkpoint":
                    slot["approve"] |= a.answer.strip().lower().startswith(APPROVE.lower())
                    slot["reasons"].append(a.reason())
                elif a.header == "pick":
                    slot["pick"] = True
                    slot["chosen"] += [] if a.answer.strip().lower() == KEEP_ALL.lower() else CANDIDATE.findall(a.answer)
                    slot["reasons"].append(a.reason())
                else:
                    slot["chosen"] += LITERATURE.findall(a.answer)
        except (FragPlaceError, ValueError, AttributeError) as e:
            said.append(f"[{a.study}] not recorded: {e}")
    for (study, cp), slot in pending.items():
        if not (slot["approve"] or slot["pick"]):
            said.append(f"[{study}] '{cp}' not passed: the answer was not Approve; ask what to change")
            continue
        try:
            choice = record_choice(root, study, cp, list(dict.fromkeys(slot["chosen"])), " | ".join(slot["reasons"]), who)
            said.append(f"[{study}] '{cp}' passed by {who}" + (f"; chosen {', '.join(choice.chosen)}" if choice.chosen else ""))
            if any(LITERATURE.fullmatch(x) for x in choice.chosen):
                refresh_literature(Study(root, study))
        except FragPlaceError as e:
            said.append(f"[{study}] '{cp}' not passed: {e}")
    return said


def _value(text: str) -> Any:
    """A decision's value: JSON when the answer parses as JSON, so 5.0, true and ["a", "b"] keep their type; else the text."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text.strip()


def main() -> None:
    """The PostToolUse hook: never fails the tool call; tells the model what was recorded."""
    try:
        said = record(json.load(sys.stdin))
    except Exception as e:  # noqa: BLE001 - a hook must not break the chat; the model is told instead
        said = [f"FragPlace could not read the answers: {type(e).__name__}: {e}"]
    if said:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "FragPlace recorded: " + " | ".join(said)}}))


if __name__ == "__main__":
    main()
