"""Tests for stop_policy mechanism."""

import pytest

from actor_for_agents import Actor, ActorSystem, StopMode, AfterMessage, AfterIdle, StopPolicy


class OneTimeActor(Actor):
    """Actor that stops after processing one message."""

    def stop_policy(self) -> StopPolicy:
        return StopMode.ONE_TIME

    async def on_receive(self, message):
        return f"processed: {message}"


class AfterMessageActor(Actor):
    """Actor that stops after receiving 'stop' message."""

    def stop_policy(self) -> StopPolicy:
        return AfterMessage(message="stop")

    async def on_receive(self, message):
        return f"processed: {message}"


class AfterIdleActor(Actor):
    """Actor that stops after 0.5 seconds of idle time."""

    def stop_policy(self) -> StopPolicy:
        return AfterIdle(seconds=0.5)

    async def on_receive(self, message):
        return f"processed: {message}"


class NeverStopActor(Actor):
    """Actor with default NEVER policy."""

    async def on_receive(self, message):
        return f"processed: {message}"


@pytest.mark.anyio
async def test_one_time_actor_stops_after_one_message():
    """ONE_TIME actor stops after processing one message."""
    system = ActorSystem()
    try:
        ref = await system.spawn(OneTimeActor, "one-time")
        assert ref.is_alive

        # Send first message
        result = await ref.ask("first")
        assert result == "processed: first"

        # Actor should stop after processing one message
        import asyncio
        await asyncio.sleep(0.1)
        assert not ref.is_alive
    finally:
        await system.shutdown()


@pytest.mark.anyio
async def test_after_message_actor_stops_on_specific_message():
    """AfterMessage actor stops when it receives the specific message."""
    system = ActorSystem()
    try:
        ref = await system.spawn(AfterMessageActor, "after-msg")
        assert ref.is_alive

        # Send some messages
        result1 = await ref.ask("msg1")
        assert result1 == "processed: msg1"
        assert ref.is_alive

        result2 = await ref.ask("msg2")
        assert result2 == "processed: msg2"
        assert ref.is_alive

        # Send the stop message
        result3 = await ref.ask("stop")
        assert result3 == "processed: stop"

        # Actor should stop
        import asyncio
        await asyncio.sleep(0.1)
        assert not ref.is_alive
    finally:
        await system.shutdown()


@pytest.mark.anyio
async def test_after_idle_actor_stops_after_timeout():
    """AfterIdle actor stops after being idle for N seconds."""
    system = ActorSystem()
    try:
        ref = await system.spawn(AfterIdleActor, "after-idle")
        assert ref.is_alive

        # Send first message
        result = await ref.ask("first")
        assert result == "processed: first"
        assert ref.is_alive

        # Wait for idle timeout (0.5 seconds + buffer)
        import asyncio
        await asyncio.sleep(0.7)
        assert not ref.is_alive
    finally:
        await system.shutdown()


@pytest.mark.anyio
async def test_tell_type_error_on_never_policy():
    """tell() raises TypeError when target actor has NEVER stop_policy."""
    from actor_for_agents import Actor, StopMode, StopPolicy

    class CallerActor(Actor):
        async def on_receive(self, message):
            if message == "test":
                try:
                    await self.tell(NeverStopActor, "hello")
                    return "no_error"
                except TypeError as e:
                    return str(e)
            return "done"

    system = ActorSystem()
    try:
        caller = await system.spawn(CallerActor, "caller")
        result = await caller.ask("test")
        assert "non-NEVER stop_policy" in result
    finally:
        await system.shutdown()


@pytest.mark.anyio
async def test_tell_succeeds_on_one_time_actor():
    """tell() succeeds when target actor has ONE_TIME policy."""
    from actor_for_agents import Actor, StopMode, StopPolicy

    class CallerActor(Actor):
        async def on_receive(self, message):
            if message == "test":
                await self.tell(OneTimeActor, "hello")
                return "ok"
            return "done"

    system = ActorSystem()
    try:
        caller = await system.spawn(CallerActor, "caller")
        result = await caller.ask("test")
        assert result == "ok"
    finally:
        await system.shutdown()


@pytest.mark.anyio
async def test_never_stop_actor_runs_forever_until_stopped():
    """NEVER actor doesn't auto-stop, must be manually stopped."""
    system = ActorSystem()
    try:
        ref = await system.spawn(NeverStopActor, "never-stop")
        assert ref.is_alive

        # Send multiple messages
        for i in range(5):
            result = await ref.ask(f"msg{i}")
            assert result == f"processed: msg{i}"
            assert ref.is_alive

        # Manually stop
        ref.stop()
        import asyncio
        await asyncio.sleep(0.1)
        assert not ref.is_alive
    finally:
        await system.shutdown()
