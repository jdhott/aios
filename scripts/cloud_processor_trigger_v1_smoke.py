#!/usr/bin/env python3
from unittest.mock import patch

import aios.api.app as api_module
from aios.processing.trigger_coordinator import (
    ProcessingRequest,
)


class FakeCoordinator:
    released = False

    def __init__(self, _store):
        pass

    def request_processing(self):
        return ProcessingRequest(
            should_trigger=True,
            running=False,
            trigger_pending=True,
            processing_requested=True,
        )

    def release_trigger_claim(self):
        FakeCoordinator.released = True
        return {"released": True}


class FakeTrigger:
    called = False

    def trigger(self):
        FakeTrigger.called = True
        return {"name": "operations/test"}


with patch.object(
    api_module,
    "ProcessingTriggerCoordinator",
    FakeCoordinator,
), patch.object(
    api_module,
    "CloudRunJobTrigger",
    FakeTrigger,
), patch.dict(
    "os.environ",
    {"AIOS_PROCESSOR_TRIGGER_ENABLED": "true"},
    clear=False,
):
    api_module._request_processor_run()

assert FakeTrigger.called
assert not FakeCoordinator.released

print("New processing request triggers Cloud Run Job: PASS")


class BusyCoordinator(FakeCoordinator):
    def request_processing(self):
        return ProcessingRequest(
            should_trigger=False,
            running=True,
            trigger_pending=False,
            processing_requested=True,
        )


FakeTrigger.called = False

with patch.object(
    api_module,
    "ProcessingTriggerCoordinator",
    BusyCoordinator,
), patch.object(
    api_module,
    "CloudRunJobTrigger",
    FakeTrigger,
), patch.dict(
    "os.environ",
    {"AIOS_PROCESSOR_TRIGGER_ENABLED": "true"},
    clear=False,
):
    api_module._request_processor_run()

assert not FakeTrigger.called

print("Overlapping processor trigger suppressed: PASS")


class FailingTrigger:
    def trigger(self):
        raise RuntimeError("synthetic Cloud Run failure")


FakeCoordinator.released = False

with patch.object(
    api_module,
    "ProcessingTriggerCoordinator",
    FakeCoordinator,
), patch.object(
    api_module,
    "CloudRunJobTrigger",
    FailingTrigger,
), patch.dict(
    "os.environ",
    {"AIOS_PROCESSOR_TRIGGER_ENABLED": "true"},
    clear=False,
):
    api_module._request_processor_run()

assert FakeCoordinator.released

print("Failed trigger releases claim without losing request: PASS")
print("RESULT: CLOUD PROCESSOR TRIGGER V1 SMOKE TEST PASSED")
