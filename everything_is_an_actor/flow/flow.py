"""Flow ADT — syntax tree for composable agent workflows.

Flow[I, O] is a morphism I -> O in a free symmetric monoidal category.
All combinators build ADT nodes (data) — no execution until interpreted.

Concurrency primitives (categorical):
    seq:     flat_map    — Monad bind / Kleisli composition
    par:     zip         — Tensor product
    map:     map         — Functor
    alt:     branch      — Coproduct dispatch
    race:    race        — First completed wins
    recover: recover     — Supervision
    divert:  divert_to   — Akka-style side-channel
    loop:    loop        — tailRecM / trace
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

A = TypeVar("A")
B = TypeVar("B")
I = TypeVar("I")
O = TypeVar("O")


# ── Control types (loop) ─────────────────────────────────

@dataclass(frozen=True)
class Continue(Generic[A]):
    """Loop continues — feed value back as next iteration's input."""

    value: A


@dataclass(frozen=True)
class Done(Generic[B]):
    """Loop terminates — produce final result."""

    value: B


# ── Flow base ────────────────────────────────────────────


class Flow(Generic[I, O]):
    """Base class for all Flow ADT variants.

    Flow[I, O] is a morphism I -> O — data, not execution.
    Use method-chain API (Scala Future style) to compose.
    """

    # -- Functor --

    def map(self, f: Callable) -> Flow:
        """Post-compose with a pure function."""
        return _Map(source=self, f=f)

    # -- Monad --

    def flat_map(self, next_flow: Flow) -> Flow:
        """Sequential composition. Output of self feeds as input to next."""
        return _FlatMap(first=self, next=next_flow)

    # -- Tensor --

    def zip(self, other: Flow) -> Flow:
        """Parallel composition (tensor product)."""
        return _Zip(left=self, right=other)

    # -- Coproduct --

    def branch(self, mapping: dict[type, Flow]) -> Flow:
        """Route by output type (isinstance dispatch)."""
        return _Branch(source=self, mapping=mapping)

    def branch_on(
        self,
        predicate: Callable,
        then: Flow,
        otherwise: Flow,
    ) -> Flow:
        """Binary predicate branch."""
        return _BranchOn(source=self, predicate=predicate, then=then, otherwise=otherwise)

    # -- Error recovery (supervision) --

    def recover(self, handler: Callable) -> Flow:
        """Recover from errors with a pure handler function."""
        return _Recover(source=self, handler=handler)

    def recover_with(self, handler: Flow) -> Flow:
        """Recover from errors with another Flow."""
        return _RecoverWith(source=self, handler=handler)

    def fallback_to(self, other: Flow) -> Flow:
        """If self fails, try other with the original input."""
        return _FallbackTo(source=self, fallback=other)

    # -- Side-channel --

    def divert_to(self, side: Flow, when: Callable) -> Flow:
        """Fire-and-forget to side flow when predicate matches."""
        return _DivertTo(source=self, side=side, when=when)

    # -- Utilities --

    def and_then(self, callback: Callable) -> Flow:
        """Tap — side-effect callback, value passes through unchanged."""
        return _AndThen(source=self, callback=callback)

    def filter(self, predicate: Callable) -> Flow:
        """Guard — raise FlowFilterError if predicate fails."""
        return _Filter(source=self, predicate=predicate)


# ── ADT variants (all frozen dataclasses) ────────────────


@dataclass(frozen=True)
class _Agent(Flow):
    """Leaf — wraps an AgentActor class."""

    cls: type


@dataclass(frozen=True)
class _Pure(Flow):
    """Lift a pure function into Flow."""

    f: Callable


@dataclass(frozen=True)
class _FlatMap(Flow):
    """Sequential composition: first then next."""

    first: Flow
    next: Flow


@dataclass(frozen=True)
class _Zip(Flow):
    """Parallel composition (tensor product)."""

    left: Flow
    right: Flow


@dataclass(frozen=True)
class _Map(Flow):
    """Post-compose with a pure function."""

    source: Flow
    f: Callable


@dataclass(frozen=True)
class _Branch(Flow):
    """Coproduct dispatch — route by isinstance on output type."""

    source: Flow
    mapping: dict  # dict[type, Flow]


@dataclass(frozen=True)
class _BranchOn(Flow):
    """Binary predicate branch."""

    source: Flow
    predicate: Callable
    then: Flow
    otherwise: Flow


@dataclass(frozen=True)
class _Race(Flow):
    """Competitive parallelism — first to complete wins."""

    flows: list  # list[Flow]


@dataclass(frozen=True)
class _Recover(Flow):
    """Recover from errors with a pure handler."""

    source: Flow
    handler: Callable


@dataclass(frozen=True)
class _RecoverWith(Flow):
    """Recover from errors with another Flow."""

    source: Flow
    handler: Flow


@dataclass(frozen=True)
class _FallbackTo(Flow):
    """If source fails, run fallback with original input."""

    source: Flow
    fallback: Flow


@dataclass(frozen=True)
class _DivertTo(Flow):
    """Side-channel — fire-and-forget when predicate matches."""

    source: Flow
    side: Flow
    when: Callable


@dataclass(frozen=True)
class _Loop(Flow):
    """tailRecM — iterate body until Done, max_iter safety bound."""

    body: Flow
    max_iter: int = 10


@dataclass(frozen=True)
class _LoopWithState(Flow):
    """Trace — loop with explicit feedback state S."""

    body: Flow
    init_state: Any = None
    max_iter: int = 10


@dataclass(frozen=True)
class _AndThen(Flow):
    """Tap — side-effect callback, passes value through unchanged."""

    source: Flow
    callback: Callable


@dataclass(frozen=True)
class _Filter(Flow):
    """Guard — raise FlowFilterError if predicate fails."""

    source: Flow
    predicate: Callable


class FlowFilterError(Exception):
    """Raised when a filter predicate fails."""

    def __init__(self, value: Any) -> None:
        self.value = value
        super().__init__(f"Flow filter rejected value: {value!r}")
