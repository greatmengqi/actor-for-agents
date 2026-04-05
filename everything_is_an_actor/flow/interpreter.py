"""Actor interpreter — evaluate Flow ADT into actor topology.

Recursive interpretation: each Flow variant maps to an actor operation.
Uses existing AgentSystem / ComposableFuture infrastructure.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from everything_is_an_actor.agents.agent_actor import AgentActor
from everything_is_an_actor.agents.system import AgentSystem
from everything_is_an_actor.agents.task import Task
from everything_is_an_actor.flow.flow import (
    Continue,
    Done,
    Flow,
    FlowFilterError,
    _Agent,
    _AndThen,
    _Branch,
    _BranchOn,
    _DivertTo,
    _FallbackTo,
    _Filter,
    _FlatMap,
    _Loop,
    _LoopWithState,
    _Map,
    _Pure,
    _Race,
    _Recover,
    _RecoverWith,
    _Zip,
)


async def interpret(flow: Flow, input: Any, system: AgentSystem) -> Any:
    """Recursively interpret a Flow ADT node into actor operations."""
    match flow:
        case _Agent(cls=cls):
            return await _interpret_agent(cls, input, system)

        case _Pure(f=f):
            return f(input)

        case _Map(source=source, f=f):
            result = await interpret(source, input, system)
            return f(result)

        case _FlatMap(first=first, next=next_flow):
            mid = await interpret(first, input, system)
            return await interpret(next_flow, mid, system)

        case _Zip(left=left, right=right):
            left_input, right_input = input
            left_task = asyncio.create_task(interpret(left, left_input, system))
            right_task = asyncio.create_task(interpret(right, right_input, system))
            try:
                left_result, right_result = await asyncio.gather(left_task, right_task)
            except Exception:
                left_task.cancel()
                right_task.cancel()
                await asyncio.gather(left_task, right_task, return_exceptions=True)
                raise
            return (left_result, right_result)

        case _Branch(source=source, mapping=mapping):
            value = await interpret(source, input, system)
            for typ, branch_flow in mapping.items():
                if isinstance(value, typ):
                    return await interpret(branch_flow, value, system)
            raise KeyError(
                f"Branch: no handler for {type(value).__name__}. "
                f"Available: {[t.__name__ for t in mapping]}"
            )

        case _BranchOn(source=source, predicate=predicate, then=then_flow, otherwise=otherwise_flow):
            value = await interpret(source, input, system)
            if predicate(value):
                return await interpret(then_flow, value, system)
            return await interpret(otherwise_flow, value, system)

        case _Race(flows=flows):
            tasks = [asyncio.create_task(interpret(f, input, system)) for f in flows]
            try:
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for t in pending:
                    t.cancel()
                # Don't await pending — losers clean up in background (fire-and-forget)
                return done.pop().result()
            except Exception:
                for t in tasks:
                    t.cancel()
                raise

        case _Recover(source=source, handler=handler):
            try:
                return await interpret(source, input, system)
            except Exception as e:
                return handler(e)

        case _RecoverWith(source=source, handler=handler):
            try:
                return await interpret(source, input, system)
            except Exception as e:
                return await interpret(handler, e, system)

        case _FallbackTo(source=source, fallback=fallback):
            try:
                return await interpret(source, input, system)
            except Exception:
                return await interpret(fallback, input, system)

        case _DivertTo(source=source, side=side, when=when):
            result = await interpret(source, input, system)
            if when(result):
                asyncio.create_task(interpret(side, result, system))
            return result

        case _AndThen(source=source, callback=callback):
            result = await interpret(source, input, system)
            callback(result)
            return result

        case _Filter(source=source, predicate=predicate):
            result = await interpret(source, input, system)
            if not predicate(result):
                raise FlowFilterError(result)
            return result

        case _Loop(body=body, max_iter=max_iter):
            current = input
            for _ in range(max_iter):
                result = await interpret(body, current, system)
                match result:
                    case Done(value=value):
                        return value
                    case Continue(value=value):
                        current = value
                    case _:
                        raise TypeError(
                            f"Loop body must return Continue or Done, got {type(result).__name__}"
                        )
            raise RuntimeError(f"Loop exceeded max_iter ({max_iter}) without producing Done")

        case _LoopWithState(body=body, init_state=init_state, max_iter=max_iter):
            state = init_state() if callable(init_state) else init_state
            current = input
            for _ in range(max_iter):
                result = await interpret(body, (current, state), system)
                match result:
                    case Done(value=value):
                        return value
                    case Continue(value=value):
                        current = value
                    case _:
                        raise TypeError(
                            f"LoopWithState body must return Continue or Done, got {type(result).__name__}"
                        )
            raise RuntimeError(f"LoopWithState exceeded max_iter ({max_iter}) without producing Done")

        case _:
            raise NotImplementedError(f"Interpreter does not handle {type(flow).__name__}")


async def _interpret_agent(cls: type[AgentActor], input: Any, system: AgentSystem) -> Any:
    """Spawn an ephemeral actor, ask, stop, return output."""
    name = f"_flow-{cls.__name__}-{uuid.uuid4().hex[:8]}"
    ref = await system.spawn(cls, name)
    try:
        result = await ref._ask(Task(input=input), timeout=30.0)
        return result.get_or_raise()
    finally:
        ref.stop()
        await ref.join()
