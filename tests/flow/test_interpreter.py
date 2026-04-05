"""Integration tests — interpret Flow ADT with real AgentSystem."""

import asyncio
from dataclasses import dataclass

import pytest

from everything_is_an_actor.agents import AgentActor, AgentSystem
from everything_is_an_actor.flow import Continue, Done, FlowFilterError, agent, loop, loop_with_state, pure, race
from everything_is_an_actor.flow.interpreter import interpret

pytestmark = pytest.mark.anyio


# ── Stub agents ──────────────────────────────────────────


class Echo(AgentActor[str, str]):
    async def execute(self, input: str) -> str:
        return input


class Upper(AgentActor[str, str]):
    async def execute(self, input: str) -> str:
        return input.upper()


class Length(AgentActor[str, int]):
    async def execute(self, input: str) -> int:
        return len(input)


class Slow(AgentActor[str, str]):
    async def execute(self, input: str) -> str:
        await asyncio.sleep(0.1)
        return f"slow:{input}"


class SlowForever(AgentActor[str, str]):
    async def execute(self, input: str) -> str:
        await asyncio.sleep(0.5)
        return "slow-forever"


class Failing(AgentActor[str, str]):
    async def execute(self, input: str) -> str:
        raise ValueError(f"boom: {input}")


@dataclass(frozen=True)
class SimpleQ:
    query: str


@dataclass(frozen=True)
class ComplexQ:
    query: str


class Classifier(AgentActor[str, SimpleQ | ComplexQ]):
    async def execute(self, input: str) -> SimpleQ | ComplexQ:
        return SimpleQ(query=input) if len(input) < 10 else ComplexQ(query=input)


class SimpleHandler(AgentActor[SimpleQ, str]):
    async def execute(self, input: SimpleQ) -> str:
        return f"simple:{input.query}"


class ComplexHandler(AgentActor[ComplexQ, str]):
    async def execute(self, input: ComplexQ) -> str:
        return f"complex:{input.query}"


class CountDown(AgentActor[int, Continue[int] | Done[str]]):
    async def execute(self, input: int) -> Continue[int] | Done[str]:
        if input <= 0:
            return Done(value="done!")
        return Continue(value=input - 1)


class AlwaysContinue(AgentActor[str, Continue[str]]):
    async def execute(self, input: str) -> Continue[str]:
        return Continue(value=input)


class Accumulator(AgentActor[tuple, Continue[str] | Done[str]]):
    async def execute(self, input: tuple) -> Continue[str] | Done[str]:
        current, history = input
        history.append(current)
        if len(history) >= 3:
            return Done(value=f"collected:{','.join(history)}")
        return Continue(value=f"next-{len(history)}")


# ── Basic: Agent, Pure, Map, FlatMap ─────────────────────


class TestBasic:
    async def test_agent(self):
        system = AgentSystem()
        try:
            assert await interpret(agent(Echo), "hello", system) == "hello"
        finally:
            await system.shutdown()

    async def test_pure(self):
        system = AgentSystem()
        try:
            assert await interpret(pure(str.upper), "hello", system) == "HELLO"
        finally:
            await system.shutdown()

    async def test_map(self):
        system = AgentSystem()
        try:
            assert await interpret(agent(Echo).map(str.upper), "hello", system) == "HELLO"
        finally:
            await system.shutdown()

    async def test_flat_map(self):
        system = AgentSystem()
        try:
            assert await interpret(agent(Echo).flat_map(agent(Upper)), "hello", system) == "HELLO"
        finally:
            await system.shutdown()

    async def test_chain(self):
        system = AgentSystem()
        try:
            flow = agent(Echo).map(lambda s: s + "!").flat_map(agent(Upper))
            assert await interpret(flow, "hi", system) == "HI!"
        finally:
            await system.shutdown()


# ── Zip (parallel) ───────────────────────────────────────


class TestZip:
    async def test_zip(self):
        system = AgentSystem()
        try:
            flow = agent(Echo).zip(agent(Upper))
            assert await interpret(flow, ("hello", "world"), system) == ("hello", "WORLD")
        finally:
            await system.shutdown()

    async def test_zip_is_concurrent(self):
        import time

        system = AgentSystem()
        try:
            flow = agent(Slow).zip(agent(Slow))
            start = time.monotonic()
            result = await interpret(flow, ("a", "b"), system)
            assert time.monotonic() - start < 0.25
            assert result == ("slow:a", "slow:b")
        finally:
            await system.shutdown()


# ── Branch ───────────────────────────────────────────────


class TestBranch:
    async def test_routes_simple(self):
        system = AgentSystem()
        try:
            flow = agent(Classifier).branch({SimpleQ: agent(SimpleHandler), ComplexQ: agent(ComplexHandler)})
            assert await interpret(flow, "hi", system) == "simple:hi"
        finally:
            await system.shutdown()

    async def test_routes_complex(self):
        system = AgentSystem()
        try:
            flow = agent(Classifier).branch({SimpleQ: agent(SimpleHandler), ComplexQ: agent(ComplexHandler)})
            assert await interpret(flow, "this is a long complex query", system) == "complex:this is a long complex query"
        finally:
            await system.shutdown()

    async def test_unmatched_raises(self):
        system = AgentSystem()
        try:
            flow = agent(Classifier).branch({ComplexQ: agent(ComplexHandler)})
            with pytest.raises(KeyError):
                await interpret(flow, "hi", system)
        finally:
            await system.shutdown()


class TestBranchOn:
    async def test_true_branch(self):
        system = AgentSystem()
        try:
            flow = agent(Length).branch_on(lambda x: x > 5, then=pure(lambda x: f"long:{x}"), otherwise=pure(lambda x: f"short:{x}"))
            assert await interpret(flow, "hello world", system) == "long:11"
        finally:
            await system.shutdown()

    async def test_false_branch(self):
        system = AgentSystem()
        try:
            flow = agent(Length).branch_on(lambda x: x > 5, then=pure(lambda x: f"long:{x}"), otherwise=pure(lambda x: f"short:{x}"))
            assert await interpret(flow, "hi", system) == "short:2"
        finally:
            await system.shutdown()


# ── Recover / FallbackTo ────────────────────────────────


class TestRecover:
    async def test_recover_catches(self):
        system = AgentSystem()
        try:
            flow = agent(Failing).recover(lambda e: f"recovered: {e}")
            assert "recovered:" in await interpret(flow, "test", system)
        finally:
            await system.shutdown()

    async def test_recover_passthrough(self):
        system = AgentSystem()
        try:
            assert await interpret(agent(Echo).recover(lambda e: "nope"), "ok", system) == "ok"
        finally:
            await system.shutdown()


class TestRecoverWith:
    async def test_recover_with_flow(self):
        system = AgentSystem()
        try:
            flow = agent(Failing).recover_with(pure(lambda e: f"flow-recovered: {type(e).__name__}"))
            assert await interpret(flow, "test", system) == "flow-recovered: ValueError"
        finally:
            await system.shutdown()


class TestFallbackTo:
    async def test_fallback_on_failure(self):
        system = AgentSystem()
        try:
            assert await interpret(agent(Failing).fallback_to(agent(Echo)), "test", system) == "test"
        finally:
            await system.shutdown()

    async def test_no_fallback_on_success(self):
        system = AgentSystem()
        try:
            assert await interpret(agent(Echo).fallback_to(agent(Upper)), "hello", system) == "hello"
        finally:
            await system.shutdown()


# ── Race ─────────────────────────────────────────────────


class TestRace:
    async def test_returns_first(self):
        system = AgentSystem()
        try:
            assert await interpret(race(agent(Echo), agent(Slow)), "test", system) == "test"
        finally:
            await system.shutdown()

    async def test_cancels_losers(self):
        import time

        system = AgentSystem()
        try:
            flow = race(agent(Echo), agent(SlowForever))
            start = time.monotonic()
            assert await interpret(flow, "fast", system) == "fast"
            assert time.monotonic() - start < 0.3  # Echo is instant
        finally:
            await system.shutdown()


# ── Loop (tailRecM) ─────────────────────────────────────


class TestLoop:
    async def test_terminates_on_done(self):
        system = AgentSystem()
        try:
            assert await interpret(loop(agent(CountDown), max_iter=10), 3, system) == "done!"
        finally:
            await system.shutdown()

    async def test_single_iteration(self):
        system = AgentSystem()
        try:
            assert await interpret(loop(agent(CountDown), max_iter=10), 0, system) == "done!"
        finally:
            await system.shutdown()

    async def test_max_iter_exceeded(self):
        system = AgentSystem()
        try:
            with pytest.raises(RuntimeError, match="max_iter"):
                await interpret(loop(agent(AlwaysContinue), max_iter=3), "stuck", system)
        finally:
            await system.shutdown()


# ── DivertTo, AndThen, Filter ────────────────────────────


class TestDivertTo:
    async def test_diverts_when_true(self):
        side_log: list[str] = []

        class Logger(AgentActor[str, None]):
            async def execute(self, input: str) -> None:
                side_log.append(input)

        system = AgentSystem()
        try:
            flow = agent(Echo).divert_to(agent(Logger), when=lambda x: len(x) > 3)
            result = await interpret(flow, "hello", system)
            assert result == "hello"
            await asyncio.sleep(0.15)
            assert side_log == ["hello"]
        finally:
            await system.shutdown()

    async def test_skips_when_false(self):
        system = AgentSystem()
        try:
            flow = agent(Echo).divert_to(agent(Echo), when=lambda x: len(x) > 100)
            assert await interpret(flow, "hi", system) == "hi"
        finally:
            await system.shutdown()


class TestAndThen:
    async def test_runs_callback(self):
        captured: list[str] = []
        system = AgentSystem()
        try:
            flow = agent(Echo).and_then(lambda x: captured.append(x))
            assert await interpret(flow, "hello", system) == "hello"
            assert captured == ["hello"]
        finally:
            await system.shutdown()


class TestFilter:
    async def test_passes(self):
        system = AgentSystem()
        try:
            assert await interpret(agent(Echo).filter(lambda x: len(x) > 0), "ok", system) == "ok"
        finally:
            await system.shutdown()

    async def test_rejects(self):
        system = AgentSystem()
        try:
            with pytest.raises(FlowFilterError):
                await interpret(agent(Echo).filter(lambda x: len(x) > 10), "hi", system)
        finally:
            await system.shutdown()


# ── LoopWithState (trace) ────────────────────────────────


class TestLoopWithState:
    async def test_accumulates(self):
        system = AgentSystem()
        try:
            flow = loop_with_state(agent(Accumulator), init_state=list, max_iter=10)
            assert await interpret(flow, "start", system) == "collected:start,next-1,next-2"
        finally:
            await system.shutdown()

    async def test_callable_init(self):
        system = AgentSystem()
        try:
            flow = loop_with_state(agent(Accumulator), init_state=list, max_iter=10)
            assert await interpret(flow, "go", system) == "collected:go,next-1,next-2"
        finally:
            await system.shutdown()
