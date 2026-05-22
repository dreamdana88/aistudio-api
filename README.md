# AI Studio API

Google AIStudio Playgroud 反代，支持 Google 会员（Pro/Ultra），支持 Gemini 原生协议格式，包含生图、工具调用、Google搜索。

[English](./README_EN.md)

## 目录

- [AI Studio API](#ai-studio-api)
  - [目录](#目录)
  - [功能](#功能)
  - [快速开始](#快速开始)
    - [直接启动](#直接启动)
    - [Docker 部署](#docker-部署)
    - [登录](#登录)
      - [CLI 模式](#cli-模式)
      - [有头模式，适合本地](#有头模式适合本地)
      - [使用 cookies 登录，有效期短](#使用-cookies-登录有效期短)
  - [使用示例](#使用示例)
    - [OpenAI 兼容接口](#openai-兼容接口)
    - [Gemini 原生接口](#gemini-原生接口)
    - [Python（OpenAI SDK）](#pythonopenai-sdk)
    - [命令行客户端](#命令行客户端)
  - [支持的模型](#支持的模型)
  - [配置](#配置)
    - [模型配置](#模型配置)
    - [安全设置](#安全设置)
  - [架构](#架构)
  - [BotGuard 原理](#botguard-原理)
  - [TODO](#todo)
  - [致谢](#致谢)
  - [License](#license)

## 功能

- **OpenAI/Anthropic 兼容** — 支持 `/v1/chat/completions`、`/v1/images/generations`、`/v1/messages`
- **Gemini 原生 API** — 同时支持 `/v1beta/models/{model}:generateContent`
- **流式输出** — SSE 流式返回
- **多轮对话** — 正确的 user/model 交替结构
- **图片输入** — 支持 base64 内联和 HTTP URL，单图/多图
- **Google 搜索** — 通过 `googleSearchRetrieval` 实时联网搜索
- **Thinking** — 返回模型思考过程（`thinking` 字段）
- **图片生成** — 通过 Gemini 图片模型生成图片
- **反检测** — 支持 Camoufox/CloakBrowser(默认)
- **BotGuard** — 自动特征匹配定位 snapshot 函数
- **多账号轮询** — round-robin / LRU / 最少限流
![alt text](image/chat.png)
## 快速开始
### 直接启动
```bash
# 克隆项目
git clone https://github.com/chrysoljq/aistudio-api.git
cd aistudio-api

# 安装依赖
pip install -r requirements.txt

# 登录 Google 账号
python3 main.py login
# 启动服务
python3 main.py server --port 8080
```

### Docker 部署


```bash
docker run -d \
  --name aistudio-api \
  --restart unless-stopped \
  -p 8080:8080 \
  -v aistudio-api-data:/app/data \
  ghcr.io/chrysoljq/aistudio-api:latest
```
### 登录
#### CLI 模式
```bash
# 启动无头浏览器进行交互式登录，支持手机确认/安全码/验证器 3 种方式
python3 main.py login

# 有头，调试或手动登录
python3 main.py login --headed
```
#### 有头模式，适合本地
首次启动后，访问 http://localhost:8080 进行 Google 账号登录，支持浏览器登录和手动导入cookies（访问）。
![alt text](image/login.png)
#### 使用 cookies 登录，有效期短
访问 https://myaccount.google.com/ ，复制 cookies 导入。仅测试过 chrome->cloakbrowser，跨内核可能不支持。重启生效。
![alt text](image/cookie.png)
## 使用示例

### OpenAI 兼容接口

```bash
# 对话（流式）
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-4-31b-it",
    "messages": [{"role": "user", "content": "你好！"}],
    "stream": true
  }'

# 图片理解
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash-preview",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBOR..."}},
        {"type": "text", "text": "这是什么？"}
      ]
    }]
  }'

# 查看模型列表
curl http://localhost:8080/v1/models \
  -H "Authorization: Bearer your-secret-token"
```

### Gemini 原生接口

```bash
# 联网搜索
curl http://localhost:8080/v1beta/models/gemini-3-flash-preview:generateContent \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"role": "user", "parts": [{"text": "今天上海天气怎么样？"}]}],
    "tools": [{"googleSearchRetrieval": {}}]
  }'
```
### Python（OpenAI SDK）

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8080/v1", api_key="your-secret-token")

# 流式对话
response = client.chat.completions.create(
    model="gemini-3-flash-preview",
    messages=[{"role": "user", "content": "你好！"}],
    stream=True,
)
for chunk in response:
    print(chunk.choices[0].delta.content or "", end="")
```

### 命令行客户端

```bash
# 快速对话
python3 main.py client "今天天气怎么样？" --search

# 附带图片
python3 main.py client "这张图是什么？" -a photo.jpg

# 生图
python3 main.py client "画一只猫" --image --save cat.png
```

## 支持的模型

| 模型 | ID | 默认 Google Search | 说明 |
|------|-----|-------------------|------|
| Gemma 4 31B | `gemma-4-31b-it` | ✅ | 默认文本模型 |
| Gemma 4 26B A4B | `gemma-4-26b-a4b-it` | ✅ | MoE，4B 激活 |
| Gemini 3 Flash | `gemini-3-flash-preview` | ❌ | 快速 |
| Gemini 3.1 Pro | `gemini-3.1-pro-preview` | ❌ | |
| Gemini 3.1 Flash Lite | `gemini-3.1-flash-lite` | ❌ | |
| Gemini 3.1 Flash Image | `gemini-3.1-flash-image-preview` | ❌ | 默认图片模型，仅限 Pro/Ultra |
| Gemini 3 Pro Image | `gemini-3-pro-image-preview` | ❌ | |


## 配置

通过环境变量或 `.env` 文件配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AISTUDIO_PORT` | `8080` | API 服务端口 |
| `AISTUDIO_CAMOUFOX_PORT` | `9222` | Camoufox 调试端口 |
| `AISTUDIO_PROXY` | 空 | 浏览器代理地址 |
| `AISTUDIO_API_KEY` | 空 | API 鉴权 key，配置后启用 Bearer / X-API-Key 鉴权 |
| `AISTUDIO_DEFAULT_TEXT_MODEL` | `gemma-4-31b-it` | 默认对话模型 |
| `AISTUDIO_DEFAULT_IMAGE_MODEL` | `gemini-3.1-flash-image-preview` | 默认图片模型 |
| `AISTUDIO_CAMOUFOX_HEADLESS` | `1` | 无头模式运行浏览器 |
| `AISTUDIO_TIMEOUT_REPLAY` | `120` | 请求超时（秒） |
| `AISTUDIO_TIMEOUT_STREAM` | `120` | 流式超时（秒） |
| `AISTUDIO_SNAPSHOT_CACHE_TTL` | `3600` | BotGuard snapshot 缓存时间 |
| `AISTUDIO_ACCOUNT_ROTATION_MODE` | `round_robin` | 轮询模式：`round_robin`、`lru`、`least_rl` |
| `AISTUDIO_ACCOUNT_COOLDOWN_SECONDS` | `60` | 限流后冷却时间 |
| `AISTUDIO_DUMP_RAW_RESPONSE` | `0` | 保存原始响应到磁盘（调试） |

### 模型配置

项目根目录支持一个额外的 `config.yaml`，用于给不同模型族补默认参数。默认读取项目根目录的 `config.yaml`，也可以用 `AISTUDIO_CONFIG_FILE` 指向别的配置文件。

当前主要用于这几类场景：

- 给 `gemma` / `gemini` / 生图模型分别设置默认行为
- 给特定模型补 `generation_config` 默认值
- 控制某些生图模型需要清空哪些 wire 下标
- 配置默认工具，例如 `google_search`
- 配置安全设置 `safety_settings`

当前仓库内置的示例：

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

`match` 支持三种方式：

- `exact`: 精确命中模型名
- `prefixes`: 前缀命中，适合 `gemma-`、`gemini-`
- `contains`: 模型名包含指定片段时命中

`generation_config_defaults` 目前支持这些常用字段：

- `response_mime_type`
- `thinking_config`
- `image_output_mode`
- `media_resolution`

其中几个字段已经做了可读化转换：

- `thinking_config.level`: `LOW` / `MEDIUM` / `HIGH` / `MINIMAL`
- `image_output_mode`: `image_only` 或 `text_and_image`
- `media_resolution`: `LOW` / `MEDIUM` / `HIGH`

也可以对单个模型单独覆盖：

```yaml
model_defaults:
  models:
    gemini-3.1-flash-image-preview:
      generation_config_defaults:
        image_output_mode: text_and_image
        media_resolution: HIGH
```

### 安全设置

`safety_settings` 目前支持这四类：

- `Harassment`
- `Hate`
- `Sexually Explicit`
- `Dangerous Content`

值范围是 `1` 到 `5`：

- `1` 表示最严格，尽量完全拦截
- `5` 表示关闭

示例：

```yaml
safety_settings:
  Harassment: 1
  Hate: 2
  Sexually Explicit: 3
  Dangerous Content: 5
```

说明：

- 文本模型会把这组配置下发到 AI Studio wire 请求
- `safety_off=true` 会直接把这四项都设为 `5`
- 当前默认的图片模型配置里 `disable_safety_settings: true`，所以生图模型会直接清空安全设置字段

## 架构

```
客户端（OpenAI SDK / curl）
    │
    ▼
┌─────────────────────┐
│   FastAPI 服务器      │  ← OpenAI + Gemini API 路由
│   /v1/chat/...       │
│   /v1beta/...        │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Wire Codec         │  ← API 格式 → AI Studio gRPC body
│   + BotGuard         │     自动特征匹配 snapshot 函数
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Camoufox 浏览器    │  ← 反指纹 Firefox，注入 cookies
│   （无头模式）        │     通过 XHR hook 发送请求
└─────────┬───────────┘
          │
          ▼
    Google AI Studio
```

**工作原理：**
1. API 请求进入，转换为 AI Studio 的 wire 格式
2. 生成 BotGuard snapshot（自动检测函数，带缓存）
3. 构造完整的 gRPC body，通过 XHR hook 注入浏览器
4. 浏览器带 cookies + BotGuard 发送请求到 Google
5. 解析响应，按请求的 API 格式返回

轮询模式：
- `round_robin` — 轮流使用
- `lru` — 最久未使用
- `least_rl` — 最少被限流

## BotGuard 原理

Google 每次请求都要求一个 BotGuard "snapshot" —— 证明请求来自真实浏览器的加密凭证。本项目：

1. 在运行时 hook 前端的 snapshot 生成函数
2. 通过特征匹配自动定位（`.snapshot({` + `content` + `yield`），无惧 Google 更新
3. 为每个请求生成合法的 snapshot

snapshot 函数名随 Google bundle 更新持续变化（Mv → Ov → Sv → ...），但特征模式保持不变。

## TODO
- [ ] 完整 webui 支持
- [ ] 完整真流式支持
- [ ] 兼容 /v1/messages

## 致谢
- https://github.com/LuanRT/BgUtils
- https://github.com/iBUHub/AIStudioToAPI
- https://linux.do

## License

MIT
