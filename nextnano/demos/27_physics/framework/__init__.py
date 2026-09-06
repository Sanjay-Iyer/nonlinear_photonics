"""Demo 27 framework: shared machinery for the staged physics campaign.

Nothing in here answers a physics question. It resolves configurations,
generates decks, enforces prerequisites, records manifests and keeps the
status file honest, so that each sub-demo package contains only the one
question it is responsible for.
"""

from __future__ import annotations

__all__ = ["Demo27Error"]


class Demo27Error(RuntimeError):
    """Raised for any Demo 27 configuration, contract or policy violation."""
