"""HTTP request schemas."""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel
from aistudio_api.config import DEFAULT_IMAGE_MODEL, DEFAULT_TEXT_MODEL


class MessageContent(BaseModel):
    type: str
    text: Optional[str] = None
    image_url: Optional[dict] = None


class Message(BaseModel):
    role: str
    content: str | list[MessageContent]
    reasoning_content: Optional[str] = None


class OpenAIFunctionDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Optional[dict[str, Any]] = None


class OpenAITool(BaseModel):
    type: str
    function: Optional[OpenAIFunctionDefinition] = None


class ChatRequest(BaseModel):
    model: str = DEFAULT_TEXT_MODEL
    messages: list[Message]
    stream: bool = False
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    max_tokens: Optional[int] = None
    tools: Optional[list[OpenAITool]] = None
    stream_options: "StreamOptions | None" = None


class StreamOptions(BaseModel):
    include_usage: bool = True


class ImageRequest(BaseModel):
    prompt: str
    model: str = DEFAULT_IMAGE_MODEL
    n: int = 1
    size: str = "1024x1024"
    google_search: bool = False
    image_search: bool = False


class ImageUrl(BaseModel):
    url: str


class ImageMessage(BaseModel):
    type: str = "image_url"
    image_url: ImageUrl


class GeminiInlineData(BaseModel):
    mimeType: str
    data: str


class GeminiFileData(BaseModel):
    mimeType: Optional[str] = None
    fileUri: str


class GeminiPart(BaseModel):
    text: Optional[str] = None
    inlineData: Optional[GeminiInlineData] = None
    fileData: Optional[GeminiFileData] = None
    thought: Optional[bool] = None
    thoughtSignature: Optional[str] = None


class GeminiContent(BaseModel):
    role: Optional[str] = None
    parts: list[GeminiPart]


class GeminiTool(BaseModel):
    codeExecution: Optional[dict[str, Any]] = None
    googleSearch: Optional[dict[str, Any]] = None
    googleSearchRetrieval: Optional[dict[str, Any]] = None
    googleMaps: Optional[dict[str, Any]] = None
    urlContext: Optional[dict[str, Any]] = None
    functionDeclarations: Optional[list[dict[str, Any]]] = None


class GeminiGenerationConfig(BaseModel):
    stopSequences: Optional[list[str]] = None
    temperature: Optional[float] = None
    topP: Optional[float] = None
    topK: Optional[int] = None
    maxOutputTokens: Optional[int] = None
    responseModalities: Optional[list[str]] = None
    responseMimeType: Optional[str] = None
    responseSchema: Optional[list[Any] | dict[str, Any]] = None
    presencePenalty: Optional[float] = None
    frequencyPenalty: Optional[float] = None
    responseLogprobs: Optional[bool] = None
    logprobs: Optional[int] = None
    mediaResolution: Optional[list[Any] | int | str] = None
    thinkingConfig: Optional[list[Any] | dict[str, Any]] = None
    imageConfig: Optional[dict[str, Any]] = None


class GeminiSafetySetting(BaseModel):
    category: str
    threshold: str


class GeminiGenerateContentRequest(BaseModel):
    contents: list[GeminiContent]
    systemInstruction: Optional[GeminiContent] = None
    tools: Optional[list[GeminiTool]] = None
    generationConfig: Optional[GeminiGenerationConfig] = None
    safetySettings: Optional[list[GeminiSafetySetting]] = None


class AnthropicContentBlock(BaseModel):
    type: str
    text: Optional[str] = None
    source: Optional[dict[str, Any]] = None
    id: Optional[str] = None
    name: Optional[str] = None
    input: Optional[dict[str, Any]] = None
    tool_use_id: Optional[str] = None
    content: Optional[Any] = None
    thinking: Optional[str] = None


class AnthropicMessage(BaseModel):
    role: str
    content: str | list[AnthropicContentBlock]


class AnthropicTool(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    input_schema: Optional[dict[str, Any]] = None
    type: Optional[str] = None


class AnthropicToolChoice(BaseModel):
    type: str
    name: Optional[str] = None
    disable_parallel_tool_use: Optional[bool] = None


class AnthropicMessageRequest(BaseModel):
    model: str = DEFAULT_TEXT_MODEL
    messages: list[AnthropicMessage]
    max_tokens: Optional[int] = None
    stream: bool = False
    system: Optional[str | list[Any]] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stop_sequences: Optional[list[str]] = None
    tools: Optional[list[AnthropicTool]] = None
    tool_choice: Optional[AnthropicToolChoice] = None
    thinking: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None


class AnthropicCountTokensRequest(BaseModel):
    model: str = DEFAULT_TEXT_MODEL
    messages: list[AnthropicMessage]
    system: Optional[str | list[Any]] = None
    tools: Optional[list[AnthropicTool]] = None
