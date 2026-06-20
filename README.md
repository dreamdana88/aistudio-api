# AI Studio API — SillyTavern 适配版

本仓库 Fork 自 [wilderye/aistudio-api](https://github.com/wilderye/aistudio-api)，其核心来源为
[chrysoljq/aistudio-api](https://github.com/chrysoljq/aistudio-api)。在保留 SillyTavern 与 Windows
适配的基础上，增加 Docker、GHCR 和 1Panel 云部署支持。

## 功能

- **OpenAI/Anthropic 兼容** — 支持 `/v1/chat/completions`、`/v1/images/generations`、`/v1/messages`
- **Gemini 原生 API** — 同时支持 `/v1beta/models/{model}:generateContent`
- **流式输出** — SSE 流式返回
- **多轮对话** — 正确的 user/model 交替结构
- **图片输入** — 支持 base64 内联和 HTTP URL，单图/多图
- **Google 搜索** — 通过 `googleSearchRetrieval` 实时联网搜索
- **思维链** — 返回模型思考过程（`reasoning_content` 字段，SillyTavern 可直接显示）
- **图片生成** — 通过 Gemini 图片模型生成图片
- **反检测** — CloakBrowser 反指纹浏览器
- **BotGuard** — 自动特征匹配定位 snapshot 函数
- **多账号轮询** — round-robin / LRU / 最少限流

## 与原版的区别

| 修改项 | 说明 |
|:---|:---|
| Windows 兼容 | 修复了 `termios` 导入崩溃和 `requirements.txt` 编码问题 |
| 一键启动 | 新增 `start.bat`，自动安装依赖、设置环境变量，双击即用 |
| 思维链兼容 | 将 `thinking` 字段改为 `reasoning_content`，SillyTavern 可正确显示 |
| 安全分类容错 | 遇到未知的安全分类（如 `CIVIC_INTEGRITY`）时自动跳过，不再崩溃 |
| 浏览器不自动更新 | 禁止 CloakBrowser 启动时自动联网检查更新 |

---

## 安装

### 前置要求

- **Python 3.11+**：[下载地址](https://www.python.org/downloads/)
  - 安装时请勾选 **"Add Python to PATH"**

### 步骤

**方式 A：下载 ZIP（推荐新手）**

1. 点击本页面右上角绿色的 **Code** 按钮 → **Download ZIP**
2. 解压到任意目录
3. 双击 `start.bat` 启动

**方式 B：Git 克隆**

```bash
git clone https://github.com/dreamdana88/aistudio-api.git
cd aistudio-api
start.bat
```

首次启动时，CloakBrowser 浏览器会自动下载（约 535 MB），请耐心等待。
如果下载失败，请手动从 [GitHub Releases](https://github.com/CloakHQ/cloakbrowser/releases) 下载 `cloakbrowser-windows-x64.zip`，解压到 `C:\Users\<你的用户名>\.cloakbrowser\` 目录。

### 云服务器 / 1Panel

RackNerd、1Panel、Docker Compose、HTTPS、更新和回退步骤见
[DEPLOYMENT.md](DEPLOYMENT.md)。公网部署必须配置至少 32 位的 `AISTUDIO_API_KEY`。

---

## 登录 Google 账号

### 网页登录（推荐）

启动后，在浏览器中访问：

```
http://127.0.0.1:8080
```

进入管理后台后，使用页面上的 Google 账号登录功能完成登录。登录信息会被缓存，后续启动无需重复登录。

> 注意：如果你设置了 `AISTUDIO_API_KEY` 环境变量，访问时会先要求输入 API Token。未设置则直接进入管理后台。

### CLI 登录

```bash
# 无头浏览器交互式登录，支持手机确认/安全码/验证器
python main.py login

# 有头模式，可手动操作浏览器
python main.py login --headed
```

### Cookies 导入

访问 https://myaccount.google.com/ ，复制 cookies 导入。仅测试过 chrome→cloakbrowser，跨内核可能不支持。重启生效。

---

## SillyTavern 配置

SillyTavern 支持两种方式连接本反代，**推荐使用方式一**。

### 方式一：自定义（兼容 OpenAI）（推荐）

| 设置项 | 值 |
|:---|:---|
| 聊天补全来源 | `自定义（兼容 OpenAI）` |
| 自定义端点（基础 URL） | `http://127.0.0.1:8080/v1` |
| 自定义 API 密钥 | 随便填一个，或留空 |
| 模型名 | `gemini-3.5-flash` 或其他支持的模型 |

> 此模式下，思维链内容会通过 `reasoning_content` 字段返回，SillyTavern 可正确显示。

### 方式二：Google AI Studio（反向代理）

| 设置项 | 值 |
|:---|:---|
| 聊天补全来源 | `Google AI Studio` |
| 反向代理地址 | `http://127.0.0.1:8080` |
| API 密钥 | 随便填一个，或留空 |

---

## 支持的模型

| 模型 | ID | 默认 Google Search | 说明 |
|:---|:---|:---|:---|
| Gemini 3.5 Flash | `gemini-3.5-flash` | ❌ | 快速 |
| Gemini 3 Flash | `gemini-3-flash-preview` | ❌ | |
| Gemini 3.1 Pro | `gemini-3.1-pro-preview` | ❌ | |
| Gemini 3.1 Flash Lite | `gemini-3.1-flash-lite` | ❌ | |
| Gemma 4 31B | `gemma-4-31b-it` | ✅ | 默认文本模型 |
| Gemma 4 26B A4B | `gemma-4-26b-a4b-it` | ✅ | MoE，4B 激活 |
| Gemini 3.1 Flash Image | `gemini-3.1-flash-image-preview` | ❌ | 生图，仅限 Pro/Ultra |
| Gemini 3 Pro Image | `gemini-3-pro-image-preview` | ❌ | 生图 |

完整列表请在启动后访问 `http://127.0.0.1:8080/v1/models`。

---

## 配置

通过环境变量或 `.env` 文件配置：

| 变量 | 默认值 | 说明 |
|:---|:---|:---|
| `AISTUDIO_PORT` | `8080` | API 服务端口 |
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

### 模型配置

项目根目录支持 `config.yaml`，用于给不同模型族补默认参数（也可通过 `AISTUDIO_CONFIG_FILE` 指定路径）。

支持的场景：

- 给 `gemma` / `gemini` / 生图模型分别设置默认行为
- 给特定模型补 `generation_config` 默认值
- 配置默认工具（如 `google_search`）
- 配置安全设置 `safety_settings`

示例：

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

`match` 支持三种方式：`exact`（精确）、`prefixes`（前缀）、`contains`（包含）。

`generation_config_defaults` 支持的字段：

| 字段 | 可选值 |
|:---|:---|
| `thinking_config.level` | `LOW` / `MEDIUM` / `HIGH` / `MINIMAL` |
| `image_output_mode` | `image_only` / `text_and_image` |
| `media_resolution` | `LOW` / `MEDIUM` / `HIGH` |
| `response_mime_type` | MIME 类型字符串 |

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

`safety_settings` 支持四个分类：

- `Harassment`（骚扰）
- `Hate`（仇恨言论）
- `Sexually Explicit`（色情内容）
- `Dangerous Content`（危险内容）

值范围 `1` 到 `5`：

| 值 | 含义 |
|:---|:---|
| `1` | 最严格，尽量完全拦截 |
| `5` | 关闭 |

---

## 致谢

- **[wilderye/aistudio-api](https://github.com/wilderye/aistudio-api)** — 本 Fork 的直接上游，提供 SillyTavern 与 Windows 适配
- **[chrysoljq/aistudio-api](https://github.com/chrysoljq/aistudio-api)** — 原版项目，本仓库的全部核心功能均来自此项目
- [LuanRT/BgUtils](https://github.com/LuanRT/BgUtils)
- [iBUHub/AIStudioToAPI](https://github.com/iBUHub/AIStudioToAPI)

## License

MIT，详见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。

## 免责声明

本项目是非官方兼容层，与 Google 无隶属或背书关系。AI Studio 页面、BotGuard、账号风控或服务条款变化都可能导致项目失效。请自行确认使用方式符合相关服务条款，不要将账号 Cookie、`auth.json`、浏览器 Profile 或 `.env` 提交到 GitHub。
