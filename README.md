# AI Studio API — SillyTavern 云部署版

将 Google AI Studio 转换为 OpenAI / Anthropic / Gemini 兼容 API，适合通过
Docker 或 1Panel 部署到云服务器，并接入 SillyTavern。

本项目 Fork 自 [wilderye/aistudio-api](https://github.com/wilderye/aistudio-api)，
核心来源为 [chrysoljq/aistudio-api](https://github.com/chrysoljq/aistudio-api)。

## 主要功能

- OpenAI、Anthropic、Gemini API 兼容
- SillyTavern 流式对话与思维链显示
- 图片输入、图片生成、Google 搜索
- 多账号轮询
- Web 管理后台与 Cookie 导入
- GHCR 镜像、持久化数据、版本更新与回退

## 推荐配置

- Linux 云服务器
- 已安装 Docker 或 1Panel
- 推荐 2 核、2.5 GB 以上内存
- 低内存服务器建议配置约 2 GB Swap
- 一个已登录 Google AI Studio 的 Google 账号（建议使用小号）

## 1Panel 部署

### 1. 创建容器编排

进入：

```text
容器 → 编排 → 创建编排
```

名称可以填写：

```text
aistudio-api
```

粘贴下面的 Compose：

```yaml
services:
  aistudio-api:
    image: ghcr.io/dreamdana88/aistudio-api:latest
    container_name: aistudio-api
    restart: unless-stopped
    init: true

    ports:
      - "18080:8080"

    environment:
      AISTUDIO_PORT: "8080"
      AISTUDIO_BROWSER: "chromium"
      AISTUDIO_BROWSER_HEADLESS: "1"
      AISTUDIO_ACCOUNTS_DIR: "/app/data/accounts"
      AISTUDIO_API_KEY: "替换成你自己的至少32位密钥"
      AISTUDIO_REQUIRE_API_KEY: "1"
      AISTUDIO_MAX_CONCURRENCY: "1"

    volumes:
      - aistudio-api-data:/app/data
      - aistudio-api-browser-cache:/root/.cloakbrowser

    mem_limit: 1800m
    cpus: 1.75
    shm_size: 512m
    pids_limit: 512

    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

    healthcheck:
      test: ["CMD", "curl", "--fail", "--silent", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      start_period: 15s
      retries: 3

volumes:
  aistudio-api-data:
    name: aistudio-api-data
  aistudio-api-browser-cache:
    name: aistudio-api-browser-cache
```

`18080:8080` 的含义：

- `18080`：服务器对外端口，可以换成其他未占用端口
- `8080`：容器内程序端口，不需要修改

API 密钥可以自己设置，但必须至少 32 位。也可以在服务器终端生成：

```bash
openssl rand -hex 32
```

不要把真实 API 密钥、Cookie 或账号文件发给别人。

### 2. 启动与放行端口

创建编排后等待容器启动。第一次启动会下载约 200 MB 的 CloakBrowser，
日志出现下载、解压和 `/health 200 OK` 属于正常现象。

在 1Panel 防火墙和云服务商防火墙中放行 TCP `18080`，然后访问：

```text
http://服务器IP:18080
```

输入 Compose 中设置的 API 密钥即可进入后台。

服务器终端也可以检查：

```bash
curl http://127.0.0.1:18080/health
```

正常会返回类似：

```json
{"status":"ok","busy":false}
```

> IP + HTTP 适合快速测试。长期公网使用建议配置域名和 HTTPS，避免 API 密钥与聊天内容明文传输。

## 导入 Google Cookie

云服务器使用无头浏览器，后台的“登录账号”通常不会在你的电脑弹出登录窗口。
推荐在自己电脑的 Chrome 中提取 Cookie，再通过后台导入。

1. Chrome 打开 <https://myaccount.google.com/> 并确认已经登录正确账号。
2. 按 `F12` 打开开发者工具。
3. 进入 **Network / 网络**。
4. 刷新页面。
5. 点击请求列表里的第一个 `myaccount.google.com`。
6. 打开 **Headers / 标头**。
7. 在 **Request Headers / 请求标头** 中找到 `Cookie`。
8. 复制 `Cookie:` 后面的完整内容，不要复制 `Cookie:` 这几个字。
9. 回到项目后台，选择 **导入 Cookies**，原样粘贴并提交。

Cookie 看起来是一整条很长的字符串，这是正常的：

```text
SID=...; SSID=...; HSID=...; SAPISID=...; ...
```

后台出现账号且状态为“激活”，说明导入基本成功。Cookie 等同于账号登录凭证，
不要提交到 GitHub、发到聊天群或放进截图。

## SillyTavern 配置

推荐选择：

```text
聊天补全来源：自定义（兼容 OpenAI）
自定义端点：http://服务器IP:18080/v1
API 密钥：Compose 中设置的 AISTUDIO_API_KEY
模型：gemini-3.5-flash
```

模型列表无法自动读取时，可以手动填写模型名称。第一次请求可能较慢，因为浏览器需要预热。

其他可用接口：

```text
OpenAI:    /v1/chat/completions
Anthropic: /v1/messages
Gemini:    /v1beta/models/{model}:generateContent
健康检查: /health
```

## 更新镜像

先记住当前使用的版本，然后在 1Panel 编排中修改镜像：

```yaml
image: ghcr.io/dreamdana88/aistudio-api:0.1.0
```

也可以使用：

```yaml
image: ghcr.io/dreamdana88/aistudio-api:latest
```

保存并重建编排即可。账号数据和浏览器缓存位于独立存储卷中，正常重建容器不会丢失。

如果新版本有问题，把镜像标签改回上一个版本并再次重建。

## 删除项目

在 1Panel 中停止并删除 `aistudio-api` 编排即可删除程序。

如果想保留账号数据，不要删除存储卷。如果想彻底清空，再删除：

```text
aistudio-api-data
aistudio-api-browser-cache
```

镜像、容器和数据卷互相独立，因此项目可以随时删除或重新部署。

## 常见问题

### 浏览器预热提示 Cookie 认证失败

首次启动且尚未导入账号时属于正常现象。导入正确 Cookie 后再测试。

### 外部无法访问

检查：

- Compose 是否为 `"18080:8080"`
- 1Panel 防火墙是否放行 TCP `18080`
- 云服务商防火墙是否放行 TCP `18080`
- 容器是否处于运行或健康状态

### 如何删除错误账号

先获取账号列表：

```bash
curl http://127.0.0.1:18080/accounts \
  -H "Authorization: Bearer 你的API密钥"
```

找到错误账号的 `id`（格式为 `acc_xxxxxxxx`），然后删除：

```bash
curl -X DELETE "http://127.0.0.1:18080/accounts/完整账号ID" \
  -H "Authorization: Bearer 你的API密钥"
```

### 想让 AI 帮忙排查

可以把本 README、Compose 和已经打码的容器日志交给 AI。请先删除或遮挡：

- `AISTUDIO_API_KEY`
- Google Cookie
- `auth.json`
- 代理账号密码
- 邮箱、服务器 IP 等不想公开的信息

更详细的 HTTPS、Swap、备份和回退说明见 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 致谢

- [wilderye/aistudio-api](https://github.com/wilderye/aistudio-api)
- [chrysoljq/aistudio-api](https://github.com/chrysoljq/aistudio-api)
- [LuanRT/BgUtils](https://github.com/LuanRT/BgUtils)
- [iBUHub/AIStudioToAPI](https://github.com/iBUHub/AIStudioToAPI)

## 免责声明

本项目是非官方兼容层，与 Google 无隶属或背书关系。Google AI Studio 页面、
BotGuard、账号风控或服务条款变化都可能导致项目失效。请自行评估使用风险，
并遵守相关服务条款。

MIT License，详见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。
