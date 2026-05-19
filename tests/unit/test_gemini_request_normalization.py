from aistudio_api.api.schemas import GeminiContent, GeminiGenerateContentRequest, GeminiGenerationConfig, GeminiPart
from aistudio_api.application.chat_service import normalize_gemini_request, normalize_openai_tools
from aistudio_api.api.schemas import ChatRequest


def test_normalize_gemini_request_exposes_generation_config_overrides():
    req = GeminiGenerateContentRequest(
        contents=[GeminiContent(role="user", parts=[GeminiPart(text="hello")])],
        generationConfig=GeminiGenerationConfig(
            stopSequences=["6"],
            temperature=1,
            topP=0.95,
            topK=64,
            maxOutputTokens=65536,
            responseMimeType="text/plain",
            responseSchema={
                "type": "object",
                "properties": {"test_response": {"type": "string"}},
                "propertyOrdering": ["test_response"],
            },
            presencePenalty=0.1,
            frequencyPenalty=0.2,
            responseLogprobs=True,
            logprobs=5,
            mediaResolution=[2, 1],
            thinkingConfig=[1, None, None, 3],
        ),
    )

    normalized = normalize_gemini_request(req, "models/gemini-3.1-flash-image-preview")

    assert normalized["generation_config_overrides"] == {
        "stop_sequences": ["6"],
        "max_tokens": 65536,
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "response_mime_type": "text/plain",
        "response_schema": [6, None, None, None, None, None, [["test_response", [1]]], None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, ["test_response"]],
        "presence_penalty": 0.1,
        "frequency_penalty": 0.2,
        "response_logprobs": True,
        "logprobs": 5,
        "media_resolution": [2, 1],
        "thinking_config": [1, None, None, 3],
    }


def test_normalize_gemini_request_encodes_function_declarations_to_wire_tools():
    req = GeminiGenerateContentRequest(
        contents=[GeminiContent(role="user", parts=[GeminiPart(text="hello")])],
        tools=[
            {
                "functionDeclarations": [
                    {
                        "name": "getWeather",
                        "description": "gets the weather for a requested city",
                        "parameters": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                            "propertyOrdering": ["city"],
                        },
                    }
                ]
            }
        ],
    )

    normalized = normalize_gemini_request(req, "models/gemma-4-31b-it")

    assert normalized["tools"] == [
        [
            None,
            [
                [
                    "getWeather",
                    "gets the weather for a requested city",
                    [6, None, None, None, None, None, [["city", [1]]], None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, ["city"]],
                ]
            ],
        ]
    ]


def test_normalize_openai_tools_encodes_function_tools_to_wire():
    req = ChatRequest(
        messages=[{"role": "user", "content": "hello"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "getWeather",
                    "description": "gets the weather for a requested city",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "propertyOrdering": ["city"],
                    },
                },
            }
        ],
    )

    assert normalize_openai_tools(req.tools) == [
        [
            None,
            [
                [
                    "getWeather",
                    "gets the weather for a requested city",
                    [6, None, None, None, None, None, [["city", [1]]], None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, ["city"]],
                ]
            ],
        ]
    ]


def test_normalize_openai_tools_omits_required_from_function_schema_wire():
    req = ChatRequest(
        messages=[{"role": "user", "content": "hello"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "browser_click",
                    "description": "Click by ref",
                    "parameters": {
                        "type": "object",
                        "properties": {"ref": {"type": "string"}},
                        "required": ["ref"],
                    },
                },
            }
        ],
    )

    schema = normalize_openai_tools(req.tools)[0][1][0][2]
    assert len(schema) <= 7 or schema[7] is None
