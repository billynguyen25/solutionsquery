from __future__ import annotations

from typing import Dict, List, Optional

from solutionsquery.agents import PERSONAS


class FakeClient:
    def __init__(self, by_persona: Optional[Dict[str, str]] = None, script: Optional[List[str]] = None):
        self.by_persona = by_persona or {}
        self.script = list(script or [])
        self.calls: List[list] = []

    def chat(self, messages, temperature=0.7, on_token=None):
        self.calls.append([dict(m) for m in messages])
        user = messages[-1]["content"] if messages else ""
        if user.startswith("The user's need:"):
            system = messages[0]["content"]
            text = ""
            for persona in PERSONAS:
                if f"You are {persona.name}," in system:
                    text = self.by_persona.get(persona.name, "")
                    break
        else:
            text = self.script.pop(0) if self.script else ""
        if on_token is not None:
            on_token(text)
        return text
