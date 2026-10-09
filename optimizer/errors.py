"""Errors the optimizer raises instead of returning a portfolio that breaks its own rules."""

from __future__ import annotations


class InfeasibleConstraints(ValueError):
    """The limits cannot all hold at once (for example caps that add up to less than 100%).

    ``details`` says which limits conflict and by how much, so a caller can explain it or decide to relax them."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


class SolverNotConverged(RuntimeError):
    """The solver stopped before it reached the optimum; its answer is not used."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}
