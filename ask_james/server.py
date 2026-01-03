"""Stdio MCP server that exposes the `james.review` tool."""
from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, Dict, List, Literal, Optional

from litellm import acompletion
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field, ValidationError

SERVER_NAME = "ask-james"
TOOL_NAME = "james.review"
DEFAULT_MODEL_ENV = "ASK_JAMES_MODEL"
DEFAULT_CONFIDENCE = "medium"

SYSTEM_PROMPT = """You are James, a trusted second-opinion engineer. Default to
a critical stance: assume proposals need improvement unless everything is
clearly correct, but never nitpick—every critique must be specific and
justified.
For every proposal you:
- affirm only the parts that are genuinely solid,
- flag anything wrong, risky, or inappropriate (with concrete reasoning),
- list missing assumptions or questions that block confidence.
Never rewrite the plan. Reply only with valid JSON that matches the
provided schema and never use markdown fences. Approve without changes
only when the plan is unmistakably sound.
"""

JSON_INSTRUCTIONS = {
    "summary": "1-2 sentence overall judgement",
    "confidence": "low | medium | high",
    "key_concerns": "array (0+) ordered by importance; each item has concern, why_it_matters, severity, optional suggested_fix",
    "positive_signals": "array of what looks solid",
    "questions": "array of questions James would ask the author",
    "next_steps": "array of concrete follow-ups",
    "assumptions_to_verify": "array of assumptions or dependencies to double-check",
}

server = Server(SERVER_NAME)


class ReviewRequest(BaseModel):
    input: str = Field(..., description="The proposal, plan, or decision for James to review.")


class ReviewConcern(BaseModel):
    concern: str
    why_it_matters: str
    severity: Literal["low", "medium", "high"] = Field(default="medium")
    suggested_fix: Optional[str] = None


class ReviewBody(BaseModel):
    summary: str
    confidence: Literal["low", "medium", "high"] = Field(default=DEFAULT_CONFIDENCE)
    key_concerns: List[ReviewConcern] = Field(default_factory=list)
    positive_signals: List[str] = Field(default_factory=list)
    questions: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    assumptions_to_verify: List[str] = Field(default_factory=list)


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """Describe the single exposed tool."""
    return [
        Tool(
            name=TOOL_NAME,
            description="Ask James for a structured second opinion about a proposal or plan.",
            inputSchema=ReviewRequest.model_json_schema(),
        )
    ]


@server.call_tool()
async def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Dispatch tool calls, currently only supporting james.review."""
    if tool_name != TOOL_NAME:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": "unknown_tool", "details": tool_name}, indent=2),
            )
        ]

    # Fail fast if model not configured
    if not (os.getenv(DEFAULT_MODEL_ENV) or os.getenv("LITELLM_MODEL")):
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": "no_model_configured", "details": "Set ASK_JAMES_MODEL or LITELLM_MODEL environment variable."}, indent=2),
            )
        ]

    try:
        request = ReviewRequest.model_validate(arguments)
    except ValidationError as exc:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": "invalid_arguments", "details": json.loads(exc.json())}, indent=2),
            )
        ]

    review_payload = await run_review(request)
    return [TextContent(type="text", text=json.dumps(review_payload, indent=2))]


def determine_model() -> str:
    model = os.getenv(DEFAULT_MODEL_ENV) or os.getenv("LITELLM_MODEL")
    if not model:
        raise RuntimeError("No model configured. Set ASK_JAMES_MODEL or LITELLM_MODEL.")
    return model


def build_prompt(request: ReviewRequest) -> str:
    lines: List[str] = [
        "# Task",
        "Provide a second-opinion review of the following work. This is a critique, not a rewrite.",
        "",
        "# Input",
        request.input.strip(),
        "",
        "# Output Instructions",
        "Return only JSON with the keys below. Make clear what is solid, what is wrong or unsuitable, and whether the author should proceed as-is.",
    ]

    for key, desc in JSON_INSTRUCTIONS.items():
        lines.append(f"- {key}: {desc}")

    lines.append(
        "Do not include markdown fences or commentary. JSON should be the only output."
    )

    return "\n".join(lines)


def extract_json_block(text: str) -> Dict[str, Any]:
    """Attempt to parse JSON even if wrapped in text/code fences."""
    stripped = text.strip()
    # Remove common triple-backtick fences if present
    if stripped.startswith("```") and stripped.endswith("```"):
        stripped = "\n".join(stripped.splitlines()[1:-1]).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if not match:
            raise
        candidate = match.group(0)
        return json.loads(candidate)


async def run_review(request: ReviewRequest) -> Dict[str, Any]:
    model = determine_model()
    user_prompt = build_prompt(request)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        completion = await acompletion(
            model=model,
            messages=messages,
            timeout=120,  # 2 minute timeout
        )
    except Exception as exc:  # pragma: no cover - surfaces liteLLM errors
        raise RuntimeError(f"LiteLLM request failed: {exc}") from exc

    content = completion.choices[0].message["content"] if isinstance(
        completion.choices[0].message, dict
    ) else completion.choices[0].message.content
    if isinstance(content, list):  # e.g., multimodal responses
        text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
        text = "\n".join(text_parts).strip()
    else:
        text = str(content).strip()

    try:
        structured = ReviewBody.model_validate(extract_json_block(text)).model_dump()
    except Exception:
        # Fall back to returning the raw response if parsing failed.
        structured = ReviewBody(
            summary="James could not produce structured output; see raw_response.",
            confidence="low",
            key_concerns=[],
            positive_signals=[],
            questions=[],
            next_steps=[],
            assumptions_to_verify=[],
        ).model_dump()
        structured["error"] = "unable_to_parse_response"

    structured["raw_response"] = text
    structured["model_used"] = model
    return structured


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
    except KeyboardInterrupt:  # pragma: no cover
        pass


if __name__ == "__main__":  # pragma: no cover
    main()
