from dataclasses import dataclass, field
from typing import Any


@dataclass
class CustomerContext:
    customer: dict
    signals: list[dict] = field(default_factory=list)
    transactions: list[dict] = field(default_factory=list)
    engagements: list[dict] = field(default_factory=list)
    behavior_analysis: dict = field(default_factory=dict)
    need_inference: dict = field(default_factory=dict)
    next_best_action: dict = field(default_factory=dict)
    message: dict = field(default_factory=dict)
    channel: dict = field(default_factory=dict)
    suppression: dict = field(default_factory=dict)
    escalation: dict = field(default_factory=dict)
    final_decision: dict = field(default_factory=dict)
    audit_events: list[dict] = field(default_factory=list)


class Agent:
    name = "Agent"

    def run(self, context: CustomerContext) -> dict:
        raise NotImplementedError
