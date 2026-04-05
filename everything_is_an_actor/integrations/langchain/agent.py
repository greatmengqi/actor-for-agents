"""LangChainAgent — declarative AgentActor backed by a LangChain ChatModel."""

from __future__ import annotations

from typing import Any, ClassVar, Generic, TypeVar

from everything_is_an_actor.agents.agent_actor import AgentActor

I = TypeVar("I")
O = TypeVar("O")

_MAX_TOOL_ROUNDS = 10


class LangChainAgent(AgentActor[I, O], Generic[I, O]):
    """AgentActor that delegates to a LangChain ChatModel.

    Class attributes configure the LLM; override execute() for custom logic.
    When tools are provided, runs a ReAct-style loop: invoke → tool calls → invoke → ...
    until the model produces a final text response (no more tool calls).

    Example::

        class Summarizer(LangChainAgent[str, str]):
            model = ChatOpenAI(model="gpt-4o-mini")
            system_prompt = "Summarize the input."

        class Researcher(LangChainAgent[str, str]):
            model = ChatOpenAI(model="gpt-4o")
            tools = [web_search]
            system_prompt = "Search and summarize."
    """

    model: ClassVar[Any] = None               # BaseChatModel
    tools: ClassVar[list] = []                 # list[BaseTool]
    system_prompt: ClassVar[str] = ""
    output_parser: ClassVar[Any] = None        # BaseOutputParser | None
    max_tool_rounds: ClassVar[int] = _MAX_TOOL_ROUNDS

    async def execute(self, input: I) -> O:
        """Invoke model, handle tool calls in a loop, parse output."""
        if self.model is None:
            raise ValueError(f"{type(self).__name__}.model is not set")

        messages: list[Any] = []

        if self.system_prompt:
            system_content = self.system_prompt
            if self.output_parser is not None and hasattr(self.output_parser, "get_format_instructions"):
                system_content += f"\n\n{self.output_parser.get_format_instructions()}"
            messages.append({"role": "system", "content": system_content})

        messages.append({"role": "user", "content": str(input)})

        bound_model = self.model.bind_tools(self.tools) if self.tools else self.model

        # Tool-calling loop: invoke → execute tool calls → feed results back → repeat
        tools_by_name = {t.name: t for t in self.tools} if self.tools else {}

        for _ in range(self.max_tool_rounds):
            response = await bound_model.ainvoke(messages)
            messages.append(response)

            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                # No tool calls — model produced final response
                break

            # Execute each tool call and append results
            for tc in tool_calls:
                tool = tools_by_name.get(tc["name"])
                if tool is None:
                    tool_output = f"Error: unknown tool '{tc['name']}'"
                else:
                    tool_output = await tool.ainvoke(tc["args"])
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": str(tool_output),
                })
        else:
            raise RuntimeError(
                f"{type(self).__name__}: tool call loop exceeded {self.max_tool_rounds} rounds"
            )

        content = response.content

        if self.output_parser is not None:
            return self.output_parser.parse(content)

        return content
