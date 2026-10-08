"""Errors the engine raises instead of building a portfolio on bad inputs or broken limits.

Each one carries a plain-language message for the person and ``details`` for code."""

from __future__ import annotations

from optimizer.errors import InfeasibleConstraints, SolverNotConverged


class RoboKitInputError(ValueError):
    """A request field is missing, out of range or not a number."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


__all__ = ["RoboKitInputError", "InfeasibleConstraints", "SolverNotConverged"]
