# Mixture of Agents (MOA)

Composable multi-agent orchestration pattern built on top of the actor/agent framework.

## Architecture Overview

```
everything_is_an_actor/
  core/       <- generic actor runtime (Actor, ActorRef, ActorSystem)
  agents/     <- AI-specific (Task, AgentActor, AgentSystem)
  moa/        <- MOA orchestration pattern
    config.py    MoATree, MoANode (recursive ADT)
    builder.py   MoABuilder (interpreter), ResolvedNode, LayerOutput
    utils.py     format_references()
```

Dependency direction: `moa/ -> agents/ -> core/`. The MOA layer is purely compositional — it uses existing primitives (`context.ask`, `ComposableFuture.recover`, `ComposableFuture.sequence`) without modifying core or agents.

## Config ADT

MOA pipelines are described as an immutable recursive data structure.

### ProposerSpec

```python
ProposerSpec = type[AgentActor] | MoATree
```

A proposer is either a leaf (an `AgentActor` class) or a subtree (a nested `MoATree`). This enables arbitrary nesting depth.

### MoANode

A single layer in the pipeline: parallel proposers followed by one aggregator.

```python
@dataclass(frozen=True)
class MoANode:
    proposers: tuple[ProposerSpec, ...]   # run in parallel
    aggregator: type[AgentActor]          # synthesizes proposer outputs
    min_success: int = 1                  # Validated threshold
    proposer_timeout: float = 30.0        # per-proposer timeout (seconds)
```

- `proposers` is normalized to a tuple in `__post_init__` (accepts list or tuple).
- `min_success` must be `>= 1` and `<= len(proposers)`.

### MoATree

An ordered sequence of `MoANode`s forming a pipeline. Each node's aggregator output becomes the next node's proposer input.

```python
@dataclass(frozen=True)
class MoATree:
    nodes: tuple[MoANode, ...]

    @classmethod
    def repeated(cls, node: MoANode, num_layers: int) -> MoATree:
        """Repeat the same node configuration N times."""
```

## Builder / Interpreter

`MoABuilder` resolves a `MoATree` into a runnable `AgentActor` class.

```python
builder = MoABuilder()
MoAAgent = builder.build(tree)    # returns type[AgentActor]
```

### Resolution process

```
MoATree -> [MoANode] -> build() -> [ResolvedNode] -> _MoAAgent
 (AST)     (unresolved)  (interpreter) (resolved)    (runtime)
```

1. `_resolve_node()` walks each `MoANode`'s proposers via `match/case`:
   - `type()` (leaf) -> kept as-is
   - `MoATree()` (subtree) -> recursively `build()` into an `AgentActor` class
2. Produces `ResolvedNode` where all proposers are concrete `type[AgentActor]`.
3. Creates a dynamic `_MoAAgent` class that holds the resolved nodes and implements `execute()`.

### ResolvedNode

```python
@dataclass(frozen=True)
class ResolvedNode:
    proposers: tuple[type[AgentActor], ...]   # all leaves
    aggregator: type[AgentActor]
    min_success: int
    proposer_timeout: float
```

## Validated Fault-Tolerance

The MOA layer uses **Validated semantics** (as opposed to fail-fast Either) for parallel proposer execution.

### How it works

Each proposer is wrapped with `context.ask(...).recover(handler)`:
- `recover()` catches `Exception` and converts it to a failed `TaskResult`.
- System errors (`MemoryError`, `SystemExit`) re-raise immediately — they are not recoverable.
- `CancelledError` (a `BaseException`) is never caught by `recover()` and propagates naturally.

After all proposers complete, the `min_success` threshold is checked:
- If `>= min_success` proposers succeeded, the pipeline continues. Failed results are included in the list passed to the aggregator.
- If `< min_success`, a `RuntimeError` is raised with details of all failures.

### Error preservation

Failed `TaskResult` objects preserve the original exception object (not `str(e)`), allowing aggregators to inspect error types:

```python
for r in results:
    if r.is_failure():
        match r.error:
            case TimeoutError():
                ...  # proposer timed out
            case ValueError() as e:
                ...  # domain error
```

## LayerOutput Directive

By default, each layer's aggregator output is passed directly as the next layer's input. For dynamic inter-layer control, an aggregator can return `LayerOutput`:

```python
from everything_is_an_actor.moa import LayerOutput

class SmartAggregator(AgentActor[list, LayerOutput]):
    async def execute(self, input: list[TaskResult]) -> LayerOutput:
        conflicts = find_conflicts(input)
        return LayerOutput(
            result=summarize(input),
            directive="focus on these disagreements" if conflicts else None,
        )
```

When the next layer's proposers receive input:
- If `directive is None`: proposers receive the raw result value.
- If `directive is not None`: proposers receive `{"input": result, "directive": directive}`.

Setting `directive=None` resets it — subsequent layers get raw input again.

## Proposer Timeout

Each `MoANode` has a `proposer_timeout` (default 30s). When a proposer exceeds this timeout:

1. `context.ask(timeout=...)` raises `TimeoutError`.
2. The framework interrupts the ephemeral actor (forced cancellation).
3. `recover()` catches the `TimeoutError` and produces a failed `TaskResult`.
4. The pipeline continues if `min_success` is still met.

This is implemented at the framework level — `_ephemeral_ask` in `ActorContext` interrupts the actor on timeout, not just on external cancellation.

## format_references Utility

A convenience function for LLM-based aggregators that need to inject proposer outputs into a prompt:

```python
from everything_is_an_actor.moa import format_references

text = format_references(results)
# Output:
# 1. [Search] quantum computing
# 2. [Analysis] quantum computing

text = format_references(results, include_failures=True)
# Output:
# 1. [Search] quantum computing
# 2. [FAILED: TimeoutError(...)]
```

This is a convenience, not a framework primitive. Aggregators can consume `list[TaskResult]` directly.

## Complete Example

```python
import asyncio
from typing import Any
from everything_is_an_actor.agents import AgentSystem, AgentActor, Task, TaskResult
from everything_is_an_actor.moa import MoATree, MoANode, MoABuilder, format_references

# Proposers
class BrainstormAgent(AgentActor[str, str]):
    async def execute(self, input: str) -> str:
        return f"Brainstorm perspective on: {input}"

class CriticAgent(AgentActor[str, str]):
    async def execute(self, input: str) -> str:
        return f"Critical analysis of: {input}"

class ResearchAgent(AgentActor[str, str]):
    async def execute(self, input: str) -> str:
        return f"Research findings for: {input}"

# Aggregator
class SynthesisAgg(AgentActor[list, str]):
    async def execute(self, input: list[TaskResult]) -> str:
        refs = format_references(input)
        return f"Synthesis of {len([r for r in input if r.is_success()])} perspectives:\n{refs}"

# Two-layer pipeline: brainstorm -> critique
tree = MoATree(nodes=[
    MoANode(
        proposers=[BrainstormAgent, CriticAgent, ResearchAgent],
        aggregator=SynthesisAgg,
        min_success=2,
        proposer_timeout=15.0,
    ),
    MoANode(
        proposers=[CriticAgent],
        aggregator=SynthesisAgg,
    ),
])

# Or use repeated() for identical layers
# tree = MoATree.repeated(
#     MoANode(proposers=[BrainstormAgent, CriticAgent], aggregator=SynthesisAgg),
#     num_layers=3,
# )

# Build and run
MoAAgent = MoABuilder().build(tree)

async def main():
    system = AgentSystem("moa")
    async for event in system.run(MoAAgent, "What is the actor model?"):
        match event.type:
            case "task_started":
                print(f"  started: {event.agent_path}")
            case "task_completed":
                print(f"  completed: {event.agent_path}")
                if event.agent_path.count("/") == 2:  # root agent
                    print(f"\nFinal result:\n{event.data}")
    await system.shutdown()

asyncio.run(main())
```

## Public API

```python
from everything_is_an_actor.moa import (
    MoATree,           # pipeline config (tuple of MoANodes)
    MoANode,           # layer config (proposers + aggregator)
    MoABuilder,        # interpreter: MoATree -> type[AgentActor]
    LayerOutput,       # optional aggregator output with directive
    ResolvedNode,      # resolved layer (all proposers are AgentActor classes)
    format_references, # prompt formatting utility
)
```
