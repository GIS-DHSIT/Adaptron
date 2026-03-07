from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeploymentArtifact:
    target: str
    path: str | None = None
    url: str | None = None
    model_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseDeployer(ABC):
    @abstractmethod
    async def deploy(self, model_path: str, **kwargs) -> DeploymentArtifact: ...
