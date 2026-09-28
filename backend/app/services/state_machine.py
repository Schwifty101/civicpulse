"""Explicit status transition table — not a chain of ifs. §2.2 domain rules."""

from app.schemas import Status

# open -> in_progress -> resolved; open -> rejected; in_progress -> rejected.
# resolved and rejected are terminal.
ALLOWED_TRANSITIONS: dict[Status, frozenset[Status]] = {
    Status.OPEN: frozenset({Status.IN_PROGRESS, Status.REJECTED}),
    Status.IN_PROGRESS: frozenset({Status.RESOLVED, Status.REJECTED}),
    Status.RESOLVED: frozenset(),
    Status.REJECTED: frozenset(),
}


class InvalidTransitionError(Exception):
    def __init__(self, current: Status, target: Status) -> None:
        self.current = current
        self.target = target
        super().__init__(f"cannot transition from '{current.value}' to '{target.value}'")


def assert_transition_allowed(current: Status, target: Status) -> None:
    if target not in ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise InvalidTransitionError(current, target)
