"""Record decisions against cached material without another model call."""

import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from ..edition import PARTICIPANT_EDITION
from ..models import WorkflowResult
from .presentation import load_context

TLX_STEPS = range(0, 101, 5)

def next_trial_id(decisions_path: Path) -> str:
    count = 0
    
    if decisions_path.exists():
        count = len(decisions_path.read_text(encoding="utf-8").splitlines())
        
    return f"trial_{count + 1:02d}"


def validate_questionnaire(data, context: dict | None = None) -> dict:
    """Check the post-trial questionnaire: the six NASA-TLX scales (0-100 in steps of 5).
    Returns a clean copy to log."""
    context = context or load_context()
    if not isinstance(data, dict):
        raise ValueError("Questionnaire must be an object")
    workload = data.get("workload")
    if not isinstance(workload, dict):
        raise ValueError("Questionnaire is missing the workload ratings")
    clean = {}
    for scale in context["workload"]:
        value = workload.get(scale["id"])
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value not in TLX_STEPS:
            raise ValueError(f"Rate {scale['name']} from 0 to 100 in steps of 5")
        clean[scale["id"]] = int(value)
    seconds = data.get("questionnaire_seconds")
    return {"workload": clean,
            "questionnaire_seconds": float(seconds) if isinstance(seconds, (int, float))
            and not isinstance(seconds, bool) else None}


class TrialSession:
    
    def __init__(self, participant_id: str, display: str, result: WorkflowResult):
        
        if not participant_id.strip():
            raise ValueError("Use a nonempty participant ID")
        
        if display not in {"2d", "xr"}:
            raise ValueError("Display must be 2d or xr")
        
        self.participant_id = participant_id
        self.display = display
        self.result = result
        self.started_at = None

    def present(self) -> dict:
        
        if self.started_at is None:
            self.started_at = perf_counter()
            
        return self.result.participant_payload()

    def record_decision(self, decision: str, path: str | Path, *,
                        decision_seconds: float | None = None, responses: dict | None = None,
                        interactions: list | None = None, questionnaire: dict | None = None) -> dict:
        """Append one decision. The web UI measures decision_seconds client-side (it stops at
        the decision, before the questionnaire) and sends Likert responses, interaction
        events (tab/panel views) and the post-trial questionnaire for later analysis."""

        if decision not in {"accept", "reject"}:
            raise ValueError("Decision must be accept or reject")

        if questionnaire is not None:
            questionnaire = validate_questionnaire(questionnaire)

        if decision_seconds is None:
            decision_seconds = perf_counter() - self.started_at

        # The participant edition has no scores; the researcher fills these in with `merge`.
        expected = (None if PARTICIPANT_EDITION else
                    self.result.metadata.get("evaluation", {}).get("correct_decision"))
        
        path = Path(path)
        trial_id = next_trial_id(path)
        
        event = {"trial_id": trial_id, "participant_id": self.participant_id,
                 "display": self.display, "cache_id": self.result.cache_id,
                 "task_id": self.result.task["id"], "architecture": self.result.architecture,
                 "decision": decision, "decision_seconds": decision_seconds,
                 "expected_decision": expected,
                 "correct": None if expected is None else decision == expected,
                 "responses": responses or {}, "questionnaire": questionnaire,
                 "interactions": interactions or [],
                 "timestamp": datetime.now(timezone.utc).isoformat()}
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event) + "\n")

        return event