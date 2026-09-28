import pytest

from app.providers.triage.base import RetryableTriageError
from app.providers.triage.simulated import SimulatedTriage


def test_deterministic_for_same_input():
    a = SimulatedTriage().triage("burst water pipe on main street", "Street 1")
    b = SimulatedTriage().triage("burst water pipe on main street", "Street 1")
    assert a == b


def test_no_network_required_by_construction():
    # SimulatedTriage never imports httpx — this just documents the guarantee CI relies on.
    import app.providers.triage.simulated as mod

    assert "httpx" not in dir(mod)


def test_fail_mode_raises_retryable_error():
    provider = SimulatedTriage(fail=True)
    with pytest.raises(RetryableTriageError):
        provider.triage("anything", "anywhere")
