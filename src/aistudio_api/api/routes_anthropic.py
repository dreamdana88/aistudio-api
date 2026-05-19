"""Anthropic-compatible API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from aistudio_api.application.api_service import handle_anthropic_messages
from aistudio_api.infrastructure.gateway.client import AIStudioClient

from .dependencies import get_client
from .schemas import AnthropicCountTokensRequest, AnthropicMessageRequest

router = APIRouter()


@router.post("/v1/messages")
async def messages(req: AnthropicMessageRequest, client: AIStudioClient = Depends(get_client)):
    return await handle_anthropic_messages(req, client)


@router.post("/v1/messages/count_tokens")
async def count_tokens(req: AnthropicCountTokensRequest):
    # Claude Desktop calls this as an auxiliary endpoint. AI Studio's browser
    # backend does not expose a cheap compatible counter here, so return a
    # conservative local estimate rather than triggering a model request.
    text = _countable_text(req)
    return {"input_tokens": max(1, len(text) // 4)}


def _countable_text(req: AnthropicCountTokensRequest) -> str:
    chunks: list[str] = []
    if isinstance(req.system, str):
        chunks.append(req.system)
    elif isinstance(req.system, list):
        for item in req.system:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict) and item.get("text"):
                chunks.append(str(item["text"]))

    for message in req.messages:
        if isinstance(message.content, str):
            chunks.append(message.content)
            continue
        for block in message.content:
            if block.text:
                chunks.append(block.text)
            elif block.type == "tool_result" and isinstance(block.content, str):
                chunks.append(block.content)

    for tool in req.tools or []:
        if tool.name:
            chunks.append(tool.name)
        if tool.description:
            chunks.append(tool.description)
    return "\n".join(chunks)
