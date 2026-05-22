# AI Studio API

Google AI Studio Playground reverse proxy. Supports Google Membership (Pro/Ultra) and the Gemini native protocol format, featuring image generation, tool calling, and Google Search.

[中文](./README.md)

## Table of Contents

- [AI Studio API](#ai-studio-api)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Quick Start](#quick-start)
    - [Direct Launch](#direct-launch)
    - [Docker Deployment](#docker-deployment)
    - [Login](#login)
      - [CLI Mode](#cli-mode)
      - [Headed Mode (Best for Local)](#headed-mode-best-for-local)
      - [Cookie Import (Short Validity)](#cookie-import-short-validity)
  - [Usage Examples](#usage-examples)
    - [OpenAI-Compatible API](#openai-compatible-api)
    - [Gemini-Native API](#gemini-native-api)
    - [Python (OpenAI SDK)](#python-openai-sdk)
    - [CLI Client](#cli-client)
  - [Supported Models](#supported-models)
  - [Configuration](#configuration)
    - [Model Configuration](#model-configuration)
    - [Safety Settings](#safety-settings)
  - [Architecture](#architecture)
  - [How BotGuard Works](#how-botguard-works)
  - [TODO](#todo)
  - [Acknowledgements](#acknowledgements)
  - [License](#license)

## Features

- **OpenAI/Anthropic Compatibility** — Supports `/v1/chat/completions`, `/v1/images/generations`, and `/v1/messages`
- **Gemini Native API** — Supports `/v1beta/models/{model}:generateContent`
- **Streaming Output** — Returns real-time results via SSE streaming
- **Multi-turn Conversations** — Properly maintains alternating `user`/`model` structure
- **Image Input** — Supports base64 inline encoding and HTTP URLs, single or multiple images
- **Google Search** — Real-time web search via `googleSearchRetrieval`
- **Thinking Process** — Returns the model's thinking process via the `thinking` field
- **Image Generation** — Generates images using Gemini image models
- **Anti-detection** — Built-in Camoufox / CloakBrowser (default) fingerprint evasion
- **BotGuard Bypass** — Automatically matches patterns to locate the `snapshot` function
- **Multi-account Rotation** — Round-robin / LRU / least rate-limited account selection

![alt text](image/chat.png)

## Quick Start

### Direct Launch

```bash
# Clone the repository
git clone https://github.com/chrysoljq/aistudio-api.git
cd aistudio-api

# Install dependencies
pip install -r requirements.txt

# Login to Google account
python3 main.py login

# Start the service
python3 main.py server --port 8080
```

### Docker Deployment

```bash
docker run -d \
  --name aistudio-api \
  --restart unless-stopped \
  -p 8080:8080 \
  -v aistudio-api-data:/app/data \
  ghcr.io/chrysoljq/aistudio-api:latest
```

### Login

#### CLI Mode

```bash
# Start headless browser for interactive login. Supports mobile confirmation, security code, or authenticator.
python3 main.py login

# Run headed browser (for debugging or manual login)
python3 main.py login --headed
```

#### Headed Mode (Best for Local)

After launching the server for the first time, visit `http://localhost:8080` to log in to your Google account. Supports direct browser login and manual cookie import.

![alt text](image/login.png)

#### Cookie Import (Short Validity)

Visit `https://myaccount.google.com/`, copy cookies, and import them. Only tested from Chrome to CloakBrowser; cross-kernel compatibility is not guaranteed. Restart the server to apply changes.

![alt text](image/cookie.png)

## Usage Examples

### OpenAI-Compatible API

```bash
# Chat (Streaming)
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-4-31b-it",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'

# Image Understanding
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash-preview",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBOR..."}},
        {"type": "text", "text": "What is this?"}
      ]
    }]
  }'

# List Models
curl http://localhost:8080/v1/models \
  -H "Authorization: Bearer your-secret-token"
```

### Gemini-Native API

```bash
# Web Search
curl http://localhost:8080/v1beta/models/gemini-3-flash-preview:generateContent \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"role": "user", "parts": [{"text": "How is the weather in Shanghai today?"}]}],
    "tools": [{"googleSearchRetrieval": {}}]
  }'
```

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8080/v1", api_key="your-secret-token")

# Streaming conversation
response = client.chat.completions.create(
    model="gemini-3-flash-preview",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True,
)
for chunk in response:
    print(chunk.choices[0].delta.content or "", end="")
```

### CLI Client

```bash
# Quick chat
python3 main.py client "How's the weather today?" --search

# With image attachment
python3 main.py client "What is in this picture?" -a photo.jpg

# Generate image
python3 main.py client "Draw a cat" --image --save cat.png
```

## Supported Models

| Model | ID | Default Google Search | Description |
|-------|----|-----------------------|-------------|
| Gemma 4 31B | `gemma-4-31b-it` | ✅ | Default text model |
| Gemma 4 26B A4B | `gemma-4-26b-a4b-it` | ✅ | MoE, 4B active |
| Gemini 3 Flash | `gemini-3-flash-preview` | ❌ | Fast |
| Gemini 3.1 Pro | `gemini-3.1-pro-preview` | ❌ | |
| Gemini 3.1 Flash Lite | `gemini-3.1-flash-lite` | ❌ | |
| Gemini 3.1 Flash Image | `gemini-3.1-flash-image-preview` | ❌ | Default image model, Pro/Ultra only |
| Gemini 3 Pro Image | `gemini-3-pro-image-preview` | ❌ | |

## Configuration

Configure via environment variables or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `AISTUDIO_PORT` | `8080` | API service port |
| `AISTUDIO_CAMOUFOX_PORT` | `9222` | Camoufox debug port |
| `AISTUDIO_PROXY` | None | Browser proxy address |
| `AISTUDIO_API_KEY` | None | API authentication key (enables Bearer / X-API-Key auth when set) |
| `AISTUDIO_DEFAULT_TEXT_MODEL` | `gemma-4-31b-it` | Default chat model |
| `AISTUDIO_DEFAULT_IMAGE_MODEL` | `gemini-3.1-flash-image-preview` | Default image model |
| `AISTUDIO_CAMOUFOX_HEADLESS` | `1` | Run browser in headless mode |
| `AISTUDIO_TIMEOUT_REPLAY` | `120` | Request timeout (seconds) |
| `AISTUDIO_TIMEOUT_STREAM` | `120` | Stream timeout (seconds) |
| `AISTUDIO_SNAPSHOT_CACHE_TTL` | `3600` | BotGuard snapshot cache duration (seconds) |
| `AISTUDIO_ACCOUNT_ROTATION_MODE` | `round_robin` | Rotation mode: `round_robin`, `lru`, `least_rl` |
| `AISTUDIO_ACCOUNT_COOLDOWN_SECONDS` | `60` | Cooldown duration after rate limit (seconds) |
| `AISTUDIO_DUMP_RAW_RESPONSE` | `0` | Save raw responses to disk (for debugging) |

### Model Configuration

An optional `config.yaml` is supported in the root directory to supply default parameters for different model families. By default, it reads the `config.yaml` in the project root, but you can use `AISTUDIO_CONFIG_FILE` to point to a different config file.

It is currently used for:

- Setting default behaviors for `gemma` / `gemini` / image models separately
- Supplementing `generation_config` default values for specific models
- Controlling which wire indexes to clear for certain image models
- Configuring default tools, such as `google_search`
- Configuring `safety_settings`

Built-in example in the repo:

```yaml
model_defaults:
  profiles:
    - name: image_models
      match:
        contains:
          - image
      is_image_model: true
      generation_config_defaults:
        response_mime_type: null
        image_output_mode: image_only
        thinking_config:
          level: MINIMAL
          mode: 1
      clear_generation_config_indexes:
        - 7
        - 13
        - 17
      disable_safety_settings: true

    - name: gemma_models
      match:
        prefixes:
          - gemma-
      default_tools:
        - google_search
      safety_settings:
        Harassment: 5
        Hate: 5
        Sexually Explicit: 5
        Dangerous Content: 5

    - name: gemini_models
      match:
        prefixes:
          - gemini-
      safety_settings:
        Harassment: 5
        Hate: 5
        Sexually Explicit: 5
        Dangerous Content: 5

  models: {}
```

`match` supports three matching modes:

- `exact`: Matches the exact model name.
- `prefixes`: Matches the prefix of the model name (e.g., `gemma-`, `gemini-`).
- `contains`: Matches if the model name contains the specified substring.

`generation_config_defaults` currently supports these common fields:

- `response_mime_type`
- `thinking_config`
- `image_output_mode`
- `media_resolution`

Several fields have human-readable wrappers:

- `thinking_config.level`: `LOW` / `MEDIUM` / `HIGH` / `MINIMAL`
- `image_output_mode`: `image_only` or `text_and_image`
- `media_resolution`: `LOW` / `MEDIUM` / `HIGH`

You can also override settings for a single model:

```yaml
model_defaults:
  models:
    gemini-3.1-flash-image-preview:
      generation_config_defaults:
        image_output_mode: text_and_image
        media_resolution: HIGH
```

### Safety Settings

`safety_settings` currently supports these four categories:

- `Harassment`
- `Hate`
- `Sexually Explicit`
- `Dangerous Content`

Values range from `1` to `5`:

- `1` represents the most restrictive (strictly block)
- `5` represents turning safety checks off

Example:

```yaml
safety_settings:
  Harassment: 1
  Hate: 2
  Sexually Explicit: 3
  Dangerous Content: 5
```

Notes:

- Text models will propagate this config group down to AI Studio wire requests.
- `safety_off=true` will directly set all four categories to `5`.
- The default image model config sets `disable_safety_settings: true`, so image models will clear safety setting fields.

## Docker Image CI

This repo includes a GitHub Actions workflow at `.github/workflows/docker.yml`.

- Changes under `src/**` trigger Docker builds on `push` and `pull_request`
- `pull_request` runs build validation only and does not push an image
- Pushes to `main` / `master` publish the image to `ghcr.io/chrysoljq/aistudio-api`
- You can also run it manually with `workflow_dispatch`

The workflow uses GitHub's built-in `GITHUB_TOKEN` for GHCR, so no separate Docker Hub account is required.

## Architecture

```
Client (OpenAI SDK / curl)
    │
    ▼
┌─────────────────────┐
│   FastAPI Server    │  ← OpenAI + Gemini API routes
│   /v1/chat/...      │
│   /v1beta/...       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Wire Codec        │  ← Converts API format → AI Studio gRPC body
│   + BotGuard        │     Auto-detects snapshot function via features
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Camoufox Browser   │  ← Anti-fingerprint Firefox, injects cookies
│  (headless)         │     Sends request via XHR hook
└─────────┬───────────┘
          │
          ▼
    Google AI Studio
```

**How it works:**
1. An API request comes in and is converted into AI Studio's wire format.
2. A BotGuard snapshot is generated (auto-detects the check function, with caching).
3. The full gRPC body is constructed and injected into the browser via XHR hook.
4. The browser sends the request to Google (with valid cookies + BotGuard).
5. The response is parsed and returned back in the requested API format.

Rotation modes:
- `round_robin` — Cycle through accounts
- `lru` — Least recently used
- `least_rl` — Least rate-limited

## How BotGuard Works

Google requires a BotGuard "snapshot" with every request — an encrypted credential proving the request originates from a real browser. This project:

1. Hooks the frontend snapshot generation function at runtime.
2. Auto-detects it via feature matching (`.snapshot({` + `content` + `yield`), resisting Google bundle updates.
3. Generates valid snapshots for each request.

The snapshot function name constantly changes with Google bundle updates (Mv → Ov → Sv → ...), but the feature pattern remains identical.

## TODO
- [ ] Complete web UI support
- [ ] Complete true streaming support
- [ ] Compatibility with `/v1/messages`

## Acknowledgements
- https://github.com/LuanRT/BgUtils
- https://github.com/iBUHub/AIStudioToAPI
- https://linux.do

## License

MIT
