"""Agentic chat engine for intercept37.

Manages multi-turn conversations with Claude, executing tools in a loop
until the model is done reasoning.  Yields streaming events so the API
layer can push them to clients via SSE.
"""

import json
import logging
import os
from typing import AsyncGenerator, Optional

import anthropic

from intercept37.agent.tools import get_tool_by_name, get_tool_schemas

logger = logging.getLogger("intercept37.agent.chat")

SYSTEM_PROMPT = """\
You are the intercept37 AI agent — an expert penetration tester and security \
analyst embedded in the intercept37 proxy suite.

You have direct access to the proxy's captured traffic, vulnerability scanner, \
and request tools. You can:
- Browse and search intercepted HTTP/HTTPS traffic
- Inspect request/response details
- Replay and modify requests
- Run automated vulnerability scans
- Analyze traffic for security issues
- Generate pentest reports

You are proactive and thorough. When asked to test something, use your tools \
to actually do it — don't just explain what you would do. Chain multiple tool \
calls together to accomplish complex tasks.

When analyzing security:
- Consider OWASP Top 10
- Look for injection points, auth issues, sensitive data exposure
- Check headers, cookies, and session handling
- Note business logic flaws, not just technical vulnerabilities
- Always note the severity (critical/high/medium/low/info)

Be concise but thorough. Show your work — explain what you found and why it \
matters.

IMPORTANT: This is for AUTHORIZED penetration testing only.\
"""


class AgentChat:
    """Manages agentic conversations backed by Claude with tool use."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
        )
        self.model = model
        # In-memory conversation store keyed by session ID.
        self.conversations: dict[str, list[dict]] = {}

    async def chat(
        self, session_id: str, user_message: str
    ) -> AsyncGenerator[dict, None]:
        """Process a user message through the agentic tool-use loop.

        Yields event dicts:
            {"type": "text",        "content": "..."}
            {"type": "tool_use",    "name": "...", "input": {...}}
            {"type": "tool_result", "name": "...", "result": {...}}
            {"type": "done"}
            {"type": "error",       "content": "..."}
        """
        if session_id not in self.conversations:
            self.conversations[session_id] = []

        messages = self.conversations[session_id]
        messages.append({"role": "user", "content": user_message})

        # --- Agentic loop: keep going while Claude wants to call tools ---
        while True:
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=get_tool_schemas(),
                    messages=messages,
                )
            except Exception as exc:
                logger.exception("Anthropic API call failed")
                yield {"type": "error", "content": str(exc)}
                return

            # Build the assistant content list and collect tool_use blocks.
            assistant_content: list[dict] = []
            tool_use_blocks: list[tuple[str, str, dict]] = []  # (id, name, input)

            for block in response.content:
                if block.type == "text":
                    yield {"type": "text", "content": block.text}
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    yield {"type": "tool_use", "name": block.name, "input": block.input}
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
                    tool_use_blocks.append((block.id, block.name, block.input))

            # Append the assistant turn.
            messages.append({"role": "assistant", "content": assistant_content})

            if not tool_use_blocks:
                # No tool calls — conversation turn is complete.
                break

            # Execute each tool ONCE and build the tool-results message.
            tool_results: list[dict] = []
            for tool_id, tool_name, tool_input in tool_use_blocks:
                tool = get_tool_by_name(tool_name)
                if tool:
                    try:
                        result = await tool.execute(**tool_input)
                    except Exception as exc:
                        logger.exception("Tool %s failed", tool_name)
                        result = {"error": str(exc)}
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}

                yield {"type": "tool_result", "name": tool_name, "result": result}

                # Serialise for the API.
                if isinstance(result, str):
                    content = result
                else:
                    content = json.dumps(result, default=str)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": content,
                })

            # Feed tool results back as a user message and loop.
            messages.append({"role": "user", "content": tool_results})

        yield {"type": "done"}

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def clear_session(self, session_id: str) -> None:
        self.conversations.pop(session_id, None)

    def get_sessions(self) -> list[str]:
        return list(self.conversations.keys())

    def get_history(self, session_id: str) -> list[dict]:
        return self.conversations.get(session_id, [])
