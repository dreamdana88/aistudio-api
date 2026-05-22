import json

import pytest

from aistudio_api.api.responses import (
    chat_completion_response,
    normalize_usage,
    sse_chunk,
    sse_usage_chunk,
    to_gemini_parts,
    to_gemini_usage_metadata,
)


def test_sse_chunk_includes_null_usage_when_requested():
    payload = sse_chunk("chatcmpl-test", "models/gemma-4-31b-it", "你好", include_usage=True)
    data = json.loads(payload.removeprefix("data: ").strip())

    assert data["choices"][0]["delta"]["content"] == "你好"
    assert "usage" in data
    assert data["usage"] is None


def test_chat_request_stream_usage_is_enabled_by_default():
    schemas = pytest.importorskip("aistudio_api.api.schemas")
    req = schemas.ChatRequest(
        model="models/gemma-4-31b-it",
        messages=[{"role": "user", "content": "你好"}],
        stream=True,
        stream_options={},
    )

    assert req.stream_options.include_usage is True


def test_sse_usage_chunk_matches_openai_style_shape():
    payload = sse_usage_chunk(
        "chatcmpl-test",
        "models/gemma-4-31b-it",
        {
            "prompt_tokens": 5,
            "completion_tokens": 161,
            "total_tokens": 166,
            "completion_tokens_details": {"reasoning_tokens": 153},
        },
    )
    data = json.loads(payload.removeprefix("data: ").strip())

    assert data["choices"] == []
    assert data["usage"] == {
        "prompt_tokens": 5,
        "completion_tokens": 161,
        "total_tokens": 166,
        "completion_tokens_details": {"reasoning_tokens": 153},
    }


def test_normalize_usage_defaults_missing_values_to_zero():
    assert normalize_usage(None).model_dump(mode="json") == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "completion_tokens_details": {"reasoning_tokens": 0},
    }


def test_normalize_usage_ignores_non_numeric_values():
    assert normalize_usage(
        {
            "prompt_tokens": [[["bad"]]],
            "completion_tokens": "7",
            "total_tokens": [1, 2, 3],
            "completion_tokens_details": {"reasoning_tokens": [5]},
        }
    ).model_dump(mode="json") == {
        "prompt_tokens": 0,
        "completion_tokens": 7,
        "total_tokens": 7,
        "completion_tokens_details": {"reasoning_tokens": 0},
    }


def test_to_gemini_usage_metadata_uses_visible_and_reasoning_tokens():
    assert to_gemini_usage_metadata(
        {
            "prompt_tokens": 9,
            "completion_tokens": 316,
            "total_tokens": 325,
            "completion_tokens_details": {"reasoning_tokens": 290, "visible_tokens": 26},
        }
    ).model_dump(mode="json") == {
        "promptTokenCount": 9,
        "candidatesTokenCount": 26,
        "thoughtsTokenCount": 290,
        "totalTokenCount": 325,
    }


def test_chat_completion_response_maps_function_calls_to_openai_tool_calls():
    response = chat_completion_response(
        model="models/gemma-4-31b-it",
        content="",
        function_calls=[{"name": "getWeather", "args": {"city": "Shanghai"}}],
    )

    choice = response.choices[0]
    assert choice.finish_reason == "tool_calls"
    assert choice.message.tool_calls[0].function.name == "getWeather"
    assert json.loads(choice.message.tool_calls[0].function.arguments) == {"city": "Shanghai"}


def test_sse_chunk_can_emit_tool_calls_delta():
    payload = sse_chunk(
        "chatcmpl-test",
        "models/gemma-4-31b-it",
        "",
        tool_calls=[
            {
                "id": "call_test",
                "type": "function",
                "function": {"name": "getWeather", "arguments": "{\"city\":\"Shanghai\"}"},
            }
        ],
        include_usage=True,
    )
    data = json.loads(payload.removeprefix("data: ").strip())

    assert data["choices"][0]["delta"]["tool_calls"][0]["function"]["name"] == "getWeather"
    assert data["usage"] is None


def test_to_gemini_parts_keeps_function_call_and_response_parts():
    parts = to_gemini_parts(
        "",
        function_calls=[{"name": "getWeather", "args": {"city": "Shanghai"}}],
        function_responses=[{"name": "getWeather", "args": {"temperature": "24C"}}],
    )

    assert [part.model_dump(mode="json", exclude_none=True) for part in parts] == [
        {"functionCall": {"name": "getWeather", "args": {"city": "Shanghai"}}},
        {"functionResponse": {"name": "getWeather", "response": {"temperature": "24C"}}},
    ]


def test_to_gemini_parts_can_emit_thought_part():
    assert [part.model_dump(mode="json", exclude_none=True) for part in to_gemini_parts("答案", thinking="思考")] == [
        {"text": "思考", "thought": True},
        {"text": "答案"},
    ]


def test_to_gemini_parts_can_emit_inline_image_data():
    from aistudio_api.domain.models import GeneratedImage

    parts = to_gemini_parts(
        "说明",
        images=[GeneratedImage(mime="image/png", data=b"png-bytes", size=9)],
    )

    assert [part.model_dump(mode="json", exclude_none=True) for part in parts] == [
        {"text": "说明"},
        {"inlineData": {"mimeType": "image/png", "data": "cG5nLWJ5dGVz"}},
    ]
