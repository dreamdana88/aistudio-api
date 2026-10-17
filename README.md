# AI Studio API — 云部署版

把 Google AI Studio 转成 OpenAI / Anthropic / Gemini 兼容 API，用 Docker 或 1Panel 部署后接入 SillyTavern。

Fork 自 [wilderye/aistudio-api](https://github.com/wilderye/aistudio-api)，核心来源 [chrysoljq/aistudio-api](https://github.com/chrysoljq/aistudio-api)。

## 功能

- OpenAI、Anthropic、Gemini 兼容接口与流式对话
- Web 后台添加账号：浏览器登录，或导入 Cookie（两种都保留）
- 图片输入/生成、Google 搜索、多账号
- 账号数据与浏览器缓存走独立卷，重建容器不会丢

## 配置建议

- Linux + Docker（或 1Panel）
- 2 核 / 2.5 GB 能跑，内存偏紧；长期使用更稳的是 4 GB，并准备约 2 GB Swap
- 一个已能打开 AI Studio 的 Google 账号（建议小号）
- API 与远程登录画面使用两个 HTTPS 子域名。画面站点由现有 Caddy 做 Basic Auth。容器端口只绑 `127.0.0.1`

## 部署

Docker 文件在 `docker/`。茶话会甲骨文部署用 `docker/docker-compose.deploy.yml`：API 默认 `127.0.0.1:18081`，noVNC 默认 `127.0.0.1:6080`。不要占用目标机酒馆的 `18080`，也不要再起一套 Caddy。

完整步骤、Caddy 示例和并发限制见 [docker/oracle-deploy.md](docker/oracle-deploy.md)。

```bash
cp .env.oracle.example .env.oracle
openssl rand -hex 32          # 写入 .env.oracle 的 AISTUDIO_API_KEY，至少 32 位
# 再写入镜像清单 digest 和 https://LOGIN_DOMAIN:8443
docker compose --env-file .env.oracle -f docker/docker-compose.deploy.yml up -d
curl http://127.0.0.1:18081/health
```

不要把真实密钥、Cookie、账号文件发到网上。公网 API 上游是 `http://127.0.0.1:18081`。若挂在子路径（例如 `/aistudio/`），反代加上 `X-Forwarded-Prefix`，酒馆端点写成 `https://API_DOMAIN:8443/aistudio/v1`。

## 添加账号

先用 API 密钥登录后台。下面两种方式都可以。

### 浏览器登录

工作浏览器始终无头。登录时临时打开有头窗口，画面经 noVNC 传到你的电脑。后台用接口返回的 `display_url`，不另开一套登录流程。

1. 用 API 密钥打开 `https://API_DOMAIN:8443`。
2. 账号管理 → 登录账号。
3. 点「打开远程画面」。先完成 Caddy Basic Auth，再在 Google 页面登录，直到进入 AI Studio。
4. 成功后账号入库。登录窗口会关掉，noVNC 变黑是正常的。

`AISTUDIO_NOVNC_PUBLIC_URL` 设为 `https://LOGIN_DOMAIN:8443`。同一时间只能有一个登录会话。关掉 noVNC 网页不会取消登录，可重连。不要把 `6080` 或 `5900` 映射到 `0.0.0.0`。未设置公网地址时，按钮才会回到 `127.0.0.1:6080`，那种情况才用 SSH 隧道。

### Cookie 导入

不想走远程画面时，继续用后台的「导入 Cookies」：

1. 本机 Chrome 打开 https://myaccount.google.com/ ，确认账号无误。
2. `F12` → Network → 刷新 → 点第一个 `myaccount.google.com` → Headers 里复制 `Cookie:` 后面的整串。
3. 粘贴到后台并提交。账号显示「激活」即可。

Cookie 就是登录凭证，不要截图、不要提交到 Git。只在 Chrome → CloakBrowser 上测过，换内核不保证能用。

## SillyTavern

```text
聊天补全来源：自定义（兼容 OpenAI）
自定义端点：https://你的域名/v1
           或 https://你的域名/aistudio/v1（子路径部署时）
API 密钥：AISTUDIO_API_KEY
模型：gemini-3.5-flash 或 gemini-3.8-flash
```

第一次请求可能较慢。部分模型的思考写在 `reasoning_content`，酒馆只渲染 `content` 时可能先看到空回复，再发一条即可。

```text
OpenAI     /v1/chat/completions
Anthropic  /v1/messages
Gemini     /v1beta/models/{model}:generateContent
健康检查   /health
```

## 更新与删除

改镜像标签后重建编排即可。不要删数据卷。当前这套部署账号卷可能是 `aistudio-api-data` 或 `aistudio-api-p1-data`，浏览器缓存是 `aistudio-api-browser-cache`。彻底清空时再删卷。

## 常见问题

**预热提示 Cookie 认证失败**  
还没添加账号时正常。先登录或导入 Cookie。

**打不开后台 / 酒馆连不上**  
API 只绑 `127.0.0.1:18081`，公网走现有 Caddy 的 `8443`。手机不要直连服务器 IP 上的 API 或 noVNC 端口。VPS 上其他容器里的 `127.0.0.1` 也不是宿主机。目标机酒馆仍占用 `18080`。

**登录后 noVNC 黑屏**  
登录浏览器已关闭，工作浏览器在无头运行，不是故障。

**删错账号**  
在后台删除，或：

```bash
curl http://127.0.0.1:18081/accounts -H "Authorization: Bearer 你的密钥"
curl -X DELETE "http://127.0.0.1:18081/accounts/acc_xxxxxxxx" -H "Authorization: Bearer 你的密钥"
```

把日志交给别人排查前，先打码 API 密钥、Cookie、`auth.json`、邮箱和服务器地址。

## 致谢

- [wilderye/aistudio-api](https://github.com/wilderye/aistudio-api)
- [chrysoljq/aistudio-api](https://github.com/chrysoljq/aistudio-api)
- [LuanRT/BgUtils](https://github.com/LuanRT/BgUtils)
- [iBUHub/AIStudioToAPI](https://github.com/iBUHub/AIStudioToAPI)

## 免责声明

非官方兼容层，与 Google 无隶属或背书。页面、风控或条款变化都可能导致失效；机房 IP 也可能触发额外验证。请自行评估风险并遵守服务条款。

MIT License，见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。
