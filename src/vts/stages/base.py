"""Base class for pipeline stages."""

from abc import ABC, abstractmethod

from vts.artifacts.store import ArtifactStore


class Stage(ABC):
    """All stages take an ArtifactStore, run logic, save artifacts, return the artifact ID."""

    def __init__(self, store: ArtifactStore):
        self.store = store

    @abstractmethod
    def run(self, **kwargs) -> str:
        """Execute the stage and return the saved artifact ID."""
        ...
