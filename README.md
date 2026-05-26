# AI Studio API — SillyTavern 适配版

基于 [chrysoljq/aistudio-api](https://github.com/chrysoljq/aistudio-api) 的 Fork，针对 [SillyTavern](https://github.com/SillyTavern/SillyTavern) 和 Windows 环境做了适配。

## 与原版的区别

| 修改项 | 说明 |
|:---|:---|
| Windows 兼容 | 修复了 `termios` 导入崩溃和 `requirements.txt` 编码问题 |
| 一键启动 | 新增 `start.bat`，自动安装依赖、设置环境变量，双击即用 |
| 思维链兼容 | 将 `thinking` 字段改为 `reasoning_content`，SillyTavern 可正确显示 |
| 安全分类容错 | 遇到未知的安全分类（如 `CIVIC_INTEGRITY`）时自动跳过，不再崩溃 |
| 浏览器不自动更新 | 禁止 CloakBrowser 启动时自动联网检查更新 |

原版的全部功能（多账号轮询、生图、Google 搜索、BotGuard、Anthropic 兼容等）均保留，详见 [原版 README](https://github.com/chrysoljq/aistudio-api)。

---

## 安装

### 前置要求

- **Python 3.11+**：[下载地址](https://www.python.org/downloads/)
  - 安装时请勾选 **"Add Python to PATH"**

### 步骤

```bash
# 1. 克隆本仓库
git clone https://github.com/wilderye/aistudio-api.git
cd aistudio-api

# 2. 双击 start.bat 启动（首次会自动安装依赖和下载浏览器）
start.bat
```

首次启动时，CloakBrowser 浏览器会自动下载（约 535 MB），请耐心等待。
如果下载失败，请手动从 [GitHub Releases](https://github.com/CloakHQ/cloakbrowser/releases) 下载 `cloakbrowser-windows-x64.zip`，解压到 `C:\Users\<你的用户名>\.cloakbrowser\` 目录。

---

## 登录 Google 账号

启动后，在浏览器中访问：

```
http://127.0.0.1:8080/login
```

完成 Google 账号登录即可。登录信息会被缓存，后续启动无需重复登录。

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

| 模型 | ID | 说明 |
|:---|:---|:---|
| Gemini 3.5 Flash | `gemini-3.5-flash` | 快速 |
| Gemini 3 Flash | `gemini-3-flash-preview` | |
| Gemini 3.1 Pro | `gemini-3.1-pro-preview` | |
| Gemma 4 31B | `gemma-4-31b-it` | 默认文本模型 |
| Gemma 4 26B A4B | `gemma-4-26b-a4b-it` | MoE |
| Gemini 3.1 Flash Image | `gemini-3.1-flash-image-preview` | 生图，仅限 Pro/Ultra |

完整列表请在启动后访问 `http://127.0.0.1:8080/v1/models`。

---

## 致谢

- **[chrysoljq/aistudio-api](https://github.com/chrysoljq/aistudio-api)** — 原版项目，本仓库的全部核心功能均来自此项目
- [LuanRT/BgUtils](https://github.com/LuanRT/BgUtils)
- [iBUHub/AIStudioToAPI](https://github.com/iBUHub/AIStudioToAPI)

## License

MIT
