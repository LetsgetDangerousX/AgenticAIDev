"""Offline agent outputs for running and demoing the study without an API key.

Researcher-only: reads experiment/demo_fixtures and reference_solutions, and is left out of
the participant edition."""

import json
from pathlib import Path

from ..models import ModelResponse

EXPERIMENT = Path(__file__).resolve().parents[3] / "experiment"
FIXTURES = EXPERIMENT / "demo_fixtures"
REFERENCES = EXPERIMENT / "reference_solutions"
APP_FILE = "app/example_calculator.py"


class DemoProvider:
    """Offline agent outputs from experiment/demo_fixtures/<task_id>.json, so the whole study
    runs without an API key. Tasks marked use_seeded get their seeded bug; seeded=True
    forces the seeded bug for any task that has one."""

    def __init__(self, seeded: bool = False):
        self.seeded = seeded
        self.model = "offline-fixture-seeded-v2" if seeded else "offline-fixture-v2"

    @property
    def cache_identity(self) -> dict:
        return {"provider": "demo", "model": self.model}

    def complete(self, *, role: str, system_prompt: str, user_prompt: str) -> ModelResponse:

        context = json.loads(user_prompt)
        task_id = context["task"]["id"]
        path = FIXTURES / f"{task_id}.json"

        if not path.is_file():
            raise ValueError(f"No demo fixture for task {task_id!r} in {FIXTURES}")

        fixture = json.loads(path.read_text(encoding="utf-8"))

        if role == "planner":
            data = fixture["planner"]

        elif role == "programmer":

            if self.seeded and "seeded_file" not in fixture:
                raise ValueError(f"Task {task_id!r} has no seeded variant")

            if self.seeded or fixture.get("use_seeded"):
                source = (FIXTURES / fixture["seeded_file"]).read_text(encoding="utf-8")
            else:
                source = (REFERENCES / task_id / APP_FILE).read_text(encoding="utf-8")

            data = {"summary": fixture["programmer_summary"], "files": {APP_FILE: source}}

        elif role == "reviewer":
            data = fixture["reviewer"]

        else:
            raise ValueError(f"Unknown role: {role}")

        return ModelResponse(json.dumps(data), self.model)


class SeededProvider:
    """Live model for every role, with Amber's planted bugs on the seeded tasks.

    Wraps a live provider (OpenAIProvider). Every role calls the live model as usual. For
    tasks whose fixture is marked use_seeded (modulo and overflow_guard, the tasks the
    schedule places one per display block), the programmer's code and summary are replaced
    by the planted-bug file before the workflow continues, so the reviewer reviews the buggy
    code live. All other tasks keep the live model's output unchanged."""

    def __init__(self, live):
        self.live = live

    @property
    def cache_identity(self) -> dict:
        return {**self.live.cache_identity, "planted_bugs": "fixtures marked use_seeded"}

    def complete(self, *, role: str, system_prompt: str, user_prompt: str) -> ModelResponse:

        response = self.live.complete(role=role, system_prompt=system_prompt, user_prompt=user_prompt)
        if role != "programmer":
            return response

        task_id = json.loads(user_prompt)["task"]["id"]
        path = FIXTURES / f"{task_id}.json"
        if not path.is_file():
            return response

        fixture = json.loads(path.read_text(encoding="utf-8"))
        if not fixture.get("use_seeded"):
            return response

        source = (FIXTURES / fixture["seeded_file"]).read_text(encoding="utf-8")
        data = {"summary": fixture["programmer_summary"], "files": {APP_FILE: source}}
        # Keep the live call's model and token counts: the call really happened.
        return ModelResponse(json.dumps(data), response.model, response.input_tokens,
                             response.output_tokens)
