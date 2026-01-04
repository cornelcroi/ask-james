"""Stdio MCP server that exposes the `james.review` tool."""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List

from litellm import acompletion
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field, ValidationError

SERVER_NAME = "ask-james"
TOOL_NAME = "james.review"

SYSTEM_PROMPT = """You are James, a trusted second-opinion engineer. Default to a critical stance: assume proposals need improvement unless everything is clearly correct, but never nitpick—every critique must be specific and justified.

For every proposal you:
- Affirm only the parts that are genuinely solid
- Flag anything wrong, risky, or inappropriate (with concrete reasoning)
- List missing assumptions or questions that block confidence

Never rewrite the plan. Approve without changes only when the plan is unmistakably sound."""

USER_PROMPT_TEMPLATE = """Review the following proposal and provide your second opinion.

Include in your response:
- A brief summary of your overall judgement
- Key concerns (if any), ordered by importance
- What looks solid
- Questions you would ask the author
- Recommended next steps
- Assumptions that should be verified

Proposal:
{input}"""

server = Server(SERVER_NAME)


class ReviewRequest(BaseModel):
    input: str = Field(..., description="The proposal, plan, or decision for James to review.")


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    return [
        Tool(
            name=TOOL_NAME,
            description="Ask James for a second opinion about a proposal or plan.",
            inputSchema=ReviewRequest.model_json_schema(),
        )
    ]


@server.call_tool()
async def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    if tool_name != TOOL_NAME:
        return [TextContent(type="text", text=f"Error: unknown tool '{tool_name}'")]

    if not (os.getenv("ASK_JAMES_MODEL") or os.getenv("LITELLM_MODEL")):
        return [TextContent(type="text", text="Error: Set ASK_JAMES_MODEL or LITELLM_MODEL environment variable.")]

    try:
        request = ReviewRequest.model_validate(arguments)
    except ValidationError as exc:
        return [TextContent(type="text", text=f"Error: invalid arguments - {exc}")]

    response = await run_review(request)
    return [TextContent(type="text", text=response)]


async def run_review(request: ReviewRequest) -> str:
    model = os.getenv("ASK_JAMES_MODEL") or os.getenv("LITELLM_MODEL")
    api_key = os.getenv("ASK_JAMES_API_KEY")
    user_prompt = USER_PROMPT_TEMPLATE.format(input=request.input.strip())

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        result = await acompletion(
            model=model,
            messages=messages,
            api_key=api_key,
            timeout=120,
        )
    except Exception as exc:
        raise RuntimeError(f"LiteLLM request failed: {exc}") from exc

    content = result.choices[0].message["content"] if isinstance(
        result.choices[0].message, dict
    ) else result.choices[0].message.content

    if isinstance(content, list):
        text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
        return "\n".join(text_parts).strip()

    return str(content).strip()


async def main_async() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            initialization_options=server.create_initialization_options(),
        )


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
