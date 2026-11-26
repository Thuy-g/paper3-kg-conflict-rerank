"""Evidence-carrying perturbation operators with label protocol v0 (docs/PLAN.md B.3)."""

from kgrerank.perturb.operators import (
    OPERATORS,
    PerturbationResult,
    QuestionFrame,
    apply_operators,
    frame_from_meta,
)

__all__ = ["OPERATORS", "PerturbationResult", "QuestionFrame", "apply_operators", "frame_from_meta"]
