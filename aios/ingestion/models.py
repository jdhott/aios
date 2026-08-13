"""Source-neutral inbox item model for AIOS ingestion.

InboxItem is intentionally Mapping-compatible during the transition so
existing pipeline code can continue to use legacy dictionary access while
new code can use source-neutral attributes.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InboxItem(Mapping[str, Any]):
    text: str
    notes: list[str] = field(default_factory=list)

    source: str = "unknown"
    source_item_id: str = ""
    source_container_id: str | None = None
    source_type: str | None = None

    _LEGACY_KEYS = (
        "text",
        "notes",
        "block_id",
        "block_type",
        "parent_block_id",
    )

    def __getitem__(self, key: str) -> Any:
        if key == "text":
            return self.text
        if key == "notes":
            return self.notes
        if key == "block_id":
            return self.source_item_id
        if key == "block_type":
            return self.source_type
        if key == "parent_block_id":
            return self.source_container_id
        if key == "source":
            return self.source
        if key == "source_item_id":
            return self.source_item_id
        if key == "source_container_id":
            return self.source_container_id
        if key == "source_type":
            return self.source_type
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(self._LEGACY_KEYS)

    def __len__(self) -> int:
        return len(self._LEGACY_KEYS)

    def to_source_neutral_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "notes": list(self.notes),
            "source": self.source,
            "source_item_id": self.source_item_id,
            "source_container_id": self.source_container_id,
            "source_type": self.source_type,
        }
