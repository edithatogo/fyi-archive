"""Typed selection of registry-owned capture automation policies."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TypedDict

from fyi_archive.instances import ArchiveInstance, AutomationPolicy, list_instances


class AutomationMatrixRow(TypedDict):
    """One GitHub Actions matrix include row."""

    instance: str
    timezone: str
    window_start_hour: int
    window_end_hour: int
    id_from: int
    id_to: int
    max_requests: int
    min_interval_seconds: float
    discovery_max_pages: int


class AutomationMatrix(TypedDict):
    """GitHub Actions matrix document."""

    include: list[AutomationMatrixRow]


@dataclass(frozen=True, slots=True)
class AutomationTarget:
    """An enabled instance and its bounded capture policy."""

    instance: ArchiveInstance
    policy: AutomationPolicy

    def matrix_row(self) -> AutomationMatrixRow:
        """Render this target as a GitHub Actions matrix include row."""
        return {
            "instance": self.instance.id,
            "timezone": self.policy.timezone,
            "window_start_hour": self.policy.window_start_hour,
            "window_end_hour": self.policy.window_end_hour,
            "id_from": self.policy.id_from,
            "id_to": self.policy.id_to,
            "max_requests": self.policy.max_requests,
            "min_interval_seconds": self.policy.min_interval_seconds,
            "discovery_max_pages": self.policy.discovery_max_pages,
        }


def select_automation_targets(
    instances: Iterable[ArchiveInstance] | None = None,
) -> tuple[AutomationTarget, ...]:
    """Return enabled automation targets in stable instance-id order."""
    candidates = list_instances() if instances is None else list(instances)
    targets = [
        AutomationTarget(instance=instance, policy=instance.automation)
        for instance in candidates
        if instance.automation is not None and instance.automation.enabled
    ]
    return tuple(sorted(targets, key=lambda target: target.instance.id))


def automation_matrix(
    instances: Iterable[ArchiveInstance] | None = None,
) -> AutomationMatrix:
    """Return enabled policies in GitHub Actions matrix form."""
    return {"include": [target.matrix_row() for target in select_automation_targets(instances)]}
