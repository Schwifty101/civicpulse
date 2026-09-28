import pytest

from app.schemas import Status
from app.services.state_machine import InvalidTransitionError, assert_transition_allowed

VALID = [
    (Status.OPEN, Status.IN_PROGRESS),
    (Status.OPEN, Status.REJECTED),
    (Status.IN_PROGRESS, Status.RESOLVED),
    (Status.IN_PROGRESS, Status.REJECTED),
]

INVALID = [
    (Status.OPEN, Status.RESOLVED),  # must pass through in_progress
    (Status.OPEN, Status.OPEN),
    (Status.RESOLVED, Status.OPEN),  # terminal
    (Status.RESOLVED, Status.IN_PROGRESS),  # terminal
    (Status.REJECTED, Status.OPEN),  # terminal
    (Status.IN_PROGRESS, Status.OPEN),  # no going back
]


@pytest.mark.parametrize("current,target", VALID)
def test_valid_transitions_allowed(current, target):
    assert_transition_allowed(current, target)  # must not raise


@pytest.mark.parametrize("current,target", INVALID)
def test_invalid_transitions_rejected(current, target):
    with pytest.raises(InvalidTransitionError) as exc_info:
        assert_transition_allowed(current, target)
    assert current.value in str(exc_info.value)
    assert target.value in str(exc_info.value)
