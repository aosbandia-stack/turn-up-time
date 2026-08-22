from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Stage(str, Enum):
    INTAKE = "INTAKE"
    DISCOVERY = "DISCOVERY"
    EVIDENCE_REVIEW = "EVIDENCE_REVIEW"
    DEFINITION = "DEFINITION"
    TICKETING = "TICKETING"
    SEAM_REVIEW = "SEAM_REVIEW"
    BUILD = "BUILD"
    INTEGRATION = "INTEGRATION"
    CLOSEOUT = "CLOSEOUT"
    RELEASE = "RELEASE"
    WORKFLOW_CLOSEOUT = "WORKFLOW_CLOSEOUT"
    DONE = "DONE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class Transition:
    source: Stage
    event: str
    target: Stage
    verdict: str
    status: str = "ACTIVE"
    loop_id: str | None = None
    max_traversals: int | None = None
    human_gate: str | None = None
    requires_new_evidence: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "source": self.source.value,
            "event": self.event,
            "target": self.target.value,
            "verdict": self.verdict,
            "status": self.status,
            "loop_id": self.loop_id,
            "max_traversals": self.max_traversals,
            "human_gate": self.human_gate,
            "requires_new_evidence": self.requires_new_evidence,
        }


# This tuple is the sole executable source of legal Tier C movement.
TRANSITIONS: tuple[Transition, ...] = (
    Transition(Stage.INTAKE, "intake_ready", Stage.DISCOVERY, "READY", human_gate="INTAKE"),
    Transition(
        Stage.INTAKE,
        "intake_ready_with_deferred_risk",
        Stage.DISCOVERY,
        "READY_WITH_DEFERRED_RISK",
        human_gate="INTAKE",
    ),
    Transition(Stage.INTAKE, "intake_blocked", Stage.BLOCKED, "INTAKE_BLOCKED", status="BLOCKED"),
    Transition(
        Stage.INTAKE,
        "intake_cancelled",
        Stage.BLOCKED,
        "CANCELLED",
        status="CANCELLED",
        human_gate="INTAKE",
    ),
    Transition(Stage.DISCOVERY, "discovery_complete", Stage.EVIDENCE_REVIEW, "DISCOVERY_COMPLETE"),
    Transition(
        Stage.DISCOVERY,
        "product_boundary_question",
        Stage.INTAKE,
        "HUMAN_PRODUCT_DECISION_REQUIRED",
        loop_id="product-boundary-return",
        max_traversals=2,
        human_gate="INTAKE",
        requires_new_evidence=True,
    ),
    Transition(Stage.DISCOVERY, "discovery_blocked", Stage.BLOCKED, "DISCOVERY_BLOCKED", status="BLOCKED"),
    Transition(Stage.EVIDENCE_REVIEW, "evidence_ready", Stage.DEFINITION, "EVIDENCE_READY"),
    Transition(
        Stage.EVIDENCE_REVIEW,
        "evidence_blocked",
        Stage.DISCOVERY,
        "EVIDENCE_BLOCKED",
        loop_id="discovery-premise-repair",
        max_traversals=2,
        requires_new_evidence=True,
    ),
    Transition(
        Stage.EVIDENCE_REVIEW,
        "product_policy_question",
        Stage.INTAKE,
        "HUMAN_PRODUCT_DECISION_REQUIRED",
        loop_id="product-boundary-return",
        max_traversals=2,
        human_gate="INTAKE",
        requires_new_evidence=True,
    ),
    Transition(
        Stage.EVIDENCE_REVIEW,
        "evidence_terminal_block",
        Stage.BLOCKED,
        "EVIDENCE_TERMINALLY_BLOCKED",
        status="BLOCKED",
    ),
    Transition(
        Stage.DEFINITION,
        "definition_approved",
        Stage.TICKETING,
        "DEFINITION_APPROVED",
        human_gate="DEFINITION",
    ),
    Transition(
        Stage.DEFINITION,
        "definition_rejected",
        Stage.BLOCKED,
        "DEFINITION_REJECTED",
        status="BLOCKED",
        human_gate="DEFINITION",
    ),
    Transition(Stage.DEFINITION, "definition_blocked", Stage.BLOCKED, "DEFINITION_BLOCKED", status="BLOCKED"),
    Transition(
        Stage.TICKETING,
        "tickets_approved",
        Stage.SEAM_REVIEW,
        "TICKETS_APPROVED",
        human_gate="TICKETS",
    ),
    Transition(
        Stage.TICKETING,
        "tickets_rejected",
        Stage.DEFINITION,
        "TICKETS_REJECTED",
        loop_id="architecture-reframe",
        max_traversals=1,
        human_gate="TICKETS",
        requires_new_evidence=True,
    ),
    Transition(Stage.TICKETING, "ticketing_blocked", Stage.BLOCKED, "TICKETING_BLOCKED", status="BLOCKED"),
    Transition(Stage.SEAM_REVIEW, "seams_sound", Stage.BUILD, "SEAMS_SOUND"),
    Transition(
        Stage.SEAM_REVIEW,
        "seams_blocked",
        Stage.TICKETING,
        "SEAMS_BLOCKED",
        loop_id="prebuild-ticket-repair",
        max_traversals=1,
        requires_new_evidence=True,
    ),
    Transition(
        Stage.SEAM_REVIEW,
        "architecture_reframe",
        Stage.DEFINITION,
        "ARCHITECTURE_REFRAME_REQUIRED",
        loop_id="architecture-reframe",
        max_traversals=1,
        requires_new_evidence=True,
    ),
    Transition(Stage.SEAM_REVIEW, "seam_review_blocked", Stage.BLOCKED, "SEAM_REVIEW_BLOCKED", status="BLOCKED"),
    Transition(Stage.BUILD, "build_complete", Stage.INTEGRATION, "BUILD_COMPLETE"),
    Transition(Stage.BUILD, "build_blocked", Stage.BLOCKED, "BUILD_BLOCKED", status="BLOCKED"),
    Transition(Stage.INTEGRATION, "seams_sound", Stage.CLOSEOUT, "SEAMS_SOUND"),
    Transition(
        Stage.INTEGRATION,
        "seams_blocked",
        Stage.BUILD,
        "SEAMS_BLOCKED",
        loop_id="integration-repair",
        max_traversals=2,
        requires_new_evidence=True,
    ),
    Transition(
        Stage.INTEGRATION,
        "architecture_escalation",
        Stage.DEFINITION,
        "ARCHITECTURE_ESCALATION",
        loop_id="architecture-reframe",
        max_traversals=1,
        requires_new_evidence=True,
    ),
    Transition(Stage.INTEGRATION, "integration_blocked", Stage.BLOCKED, "INTEGRATION_BLOCKED", status="BLOCKED"),
    Transition(Stage.CLOSEOUT, "closeout_complete", Stage.RELEASE, "CLOSEOUT_COMPLETE"),
    Transition(
        Stage.CLOSEOUT,
        "validated_repairs",
        Stage.BUILD,
        "VALIDATED_REPAIRS_REQUIRED",
        loop_id="closeout-repair",
        max_traversals=4,
        requires_new_evidence=True,
    ),
    Transition(Stage.CLOSEOUT, "closeout_blocked", Stage.BLOCKED, "CLOSEOUT_BLOCKED", status="BLOCKED"),
    Transition(
        Stage.RELEASE,
        "release_shipped",
        Stage.WORKFLOW_CLOSEOUT,
        "SHIP",
        human_gate="RELEASE",
    ),
    Transition(
        Stage.RELEASE,
        "release_shipped_with_accepted_risk",
        Stage.WORKFLOW_CLOSEOUT,
        "SHIP_WITH_ACCEPTED_RISK",
        human_gate="ACCEPTED_RISK",
    ),
    Transition(
        Stage.RELEASE,
        "release_blocked",
        Stage.BUILD,
        "RELEASE_BLOCKED",
        loop_id="release-repair",
        max_traversals=2,
        requires_new_evidence=True,
    ),
    Transition(
        Stage.RELEASE,
        "release_cancelled",
        Stage.BLOCKED,
        "CANCELLED",
        status="CANCELLED",
        human_gate="RELEASE",
    ),
    Transition(Stage.WORKFLOW_CLOSEOUT, "workflow_closed", Stage.DONE, "WORKFLOW_CLOSED", status="COMPLETE"),
    Transition(
        Stage.WORKFLOW_CLOSEOUT,
        "workflow_blocked",
        Stage.BLOCKED,
        "WORKFLOW_CLOSEOUT_BLOCKED",
        status="BLOCKED",
    ),
)

TERMINAL_STAGES = frozenset({Stage.DONE, Stage.BLOCKED})
TRANSITION_INDEX = {(transition.source, transition.event): transition for transition in TRANSITIONS}


def expected_events(stage: Stage) -> tuple[str, ...]:
    return tuple(transition.event for transition in TRANSITIONS if transition.source == stage)


def validate_topology() -> list[str]:
    errors: list[str] = []
    if len(TRANSITION_INDEX) != len(TRANSITIONS):
        errors.append("duplicate source/event transition")

    allowed_statuses = {"ACTIVE", "AWAITING_HUMAN", "BLOCKED", "COMPLETE", "CANCELLED"}
    allowed_gates = {"INTAKE", "DEFINITION", "TICKETS", "ACCEPTED_RISK", "RELEASE"}
    for transition in TRANSITIONS:
        if not transition.event.strip() or not transition.verdict.strip():
            errors.append(f"blank event or verdict from {transition.source.value}")
        if transition.status not in allowed_statuses:
            errors.append(f"invalid status {transition.status} on {transition.event}")
        if transition.human_gate and transition.human_gate not in allowed_gates:
            errors.append(f"invalid human gate {transition.human_gate} on {transition.event}")
        if transition.loop_id:
            if transition.max_traversals is None or transition.max_traversals < 1:
                errors.append(f"loop {transition.loop_id} has no positive ceiling")
        elif transition.max_traversals is not None:
            errors.append(f"non-loop transition {transition.event} has a traversal ceiling")
        if transition.requires_new_evidence and not transition.loop_id:
            errors.append(f"new-evidence transition {transition.event} is not a bounded loop")

    for stage in Stage:
        outgoing = expected_events(stage)
        if stage in TERMINAL_STAGES and outgoing:
            errors.append(f"terminal stage {stage.value} has outgoing transitions")
        if stage not in TERMINAL_STAGES and not outgoing:
            errors.append(f"nonterminal stage {stage.value} has no outgoing transitions")

    reachable = {Stage.INTAKE}
    changed = True
    while changed:
        changed = False
        for transition in TRANSITIONS:
            if transition.source in reachable and transition.target not in reachable:
                reachable.add(transition.target)
                changed = True
    missing = sorted(stage.value for stage in Stage if stage not in reachable)
    if missing:
        errors.append("unreachable stages: " + ", ".join(missing))
    if Stage.DONE not in reachable or Stage.BLOCKED not in reachable:
        errors.append("both terminal outcomes must be reachable")
    return errors
