from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aios.storage.supabase_store import SupabaseStore


PROCESSOR_TRIGGER_COORDINATOR_VERSION = "cloud-processor-trigger-v1"


@dataclass(frozen=True)
class ProcessingRequest:
    should_trigger: bool
    running: bool
    trigger_pending: bool
    processing_requested: bool


class ProcessingTriggerCoordinator:
    """Atomic Supabase-backed coordination for AIOS processor executions."""

    def __init__(self, store: SupabaseStore):
        self.store = store

    def request_processing(self) -> ProcessingRequest:
        row = self._rpc_one("request_aios_processing")
        return ProcessingRequest(
            should_trigger=bool(row.get("should_trigger")),
            running=bool(row.get("running")),
            trigger_pending=bool(row.get("trigger_pending")),
            processing_requested=bool(row.get("processing_requested")),
        )

    def release_trigger_claim(self) -> dict[str, Any]:
        return self._rpc_one("release_aios_processing_trigger")

    def begin_processing(self) -> bool:
        row = self._rpc_one("begin_aios_processing")
        return bool(row.get("acquired"))

    def finish_cycle(self) -> bool:
        row = self._rpc_one("finish_aios_processing_cycle")
        return bool(row.get("rerun_needed"))

    def mark_failed(self) -> dict[str, Any]:
        return self._rpc_one("fail_aios_processing")

    def _rpc_one(self, function_name: str) -> dict[str, Any]:
        response = (
            self.store.client
            .rpc(function_name, {})
            .execute()
        )

        data = response.data

        if isinstance(data, list):
            if not data:
                raise RuntimeError(
                    f"{function_name} returned no rows"
                )
            data = data[0]

        if not isinstance(data, dict):
            raise RuntimeError(
                f"{function_name} returned unexpected payload: {data!r}"
            )

        return data
