# 茶话会 Oracle 部署说明

这是本仓库的正式部署说明。目标机是甲骨文 ARM64 VPS。部署由原 VPS 窗口执行。本文不要求、也不授权在写出它的同时改 DNS、启动容器或重载线上 Caddy。

域名还没选定。下文的 `API_DOMAIN` 和 `LOGIN_DOMAIN` 是占位符。

## 入口

两个 HTTPS 站点都挂在已经运行的 Caddy 上，HTTPS 端口继续用 `8443`。不要再起一套 Caddy，也不要占用 `443`。

| 站点 | 上游 | 认证 |
|---|---|---|
| `https://API_DOMAIN:8443` | `127.0.0.1:18081` | 应用已有的 API Bearer 密钥 |
| `https://LOGIN_DOMAIN:8443` | `127.0.0.1:6080` | Caddy Basic Auth，覆盖整个站点 |

API 不能用 `18080`，那个端口是目标机上的酒馆。部署前再确认 `18081` 和 `6080` 没被占用。

容器只把 API 和 noVNC 发布到宿主机回环地址。原始 VNC `5900`、浏览器调试口 `9222` / `9223` 不映射。容器里的 websockify 监听 `0.0.0.0:6080` 只是容器内部地址，不能把服务改成 host 网络，否则这个端口会直接出现在公网。

远程画面沿用现有后台按钮。设置 `AISTUDIO_NOVNC_PUBLIC_URL=https://LOGIN_DOMAIN:8443` 后，登录接口返回的 `display_url` 指向该站点根路径下的 noVNC 页面，`display_via` 为 `public`。不设这个变量时仍回退到本机 SSH 隧道地址。公网部署必须设置它。登录会话管理、取消和回收都不改。

同一时间仍然只有一个登录会话。生成并发另算，见下文。

## 镜像

工作流用两台 GitHub 原生 runner 分别构建，amd64 用 `ubuntu-24.04`，arm64 用 `ubuntu-24.04-arm`，不用 QEMU。两个 job 各自推送 digest，都成功后由合并 job 用 `docker buildx imagetools create` 打同一个多架构标签。Pull request 只构建，不推送。

合并 job 会检查清单里同时有 `linux/amd64` 和 `linux/arm64`。生产使用这次清单的 digest，不使用浮动的 `latest`。

```dotenv
AISTUDIO_IMAGE=ghcr.io/dreamdana88/aistudio-api@sha256:清单摘要
```

镜像构建成功只说明包打出来了。CloakBrowser 在第一次启动时按本机架构下载二进制，缓存目录是 `/root/.cloakbrowser`，卷名 `aistudio-oracle-browser-cache`。ARM64 上下载的包名是 `cloakbrowser-linux-arm64.tar.gz`，可执行文件在 `chromium-<版本>/chrome`。`CLOAKBROWSER_AUTO_UPDATE=false`，避免缓存卷在部署后自行换成另一份二进制。浏览器是否真能在 ARM64 上打开，要等部署窗口在目标机上验证。

固定版本：

| 依赖 | 版本 | 原因 |
|---|---|---|
| cloakbrowser | 0.6.3 | 当前发行版，支持 `linux-arm64`。项目用的 `launch`、`launch_async`、`launch_persistent_context` 仍接受现有参数；`chromium_sandbox` 经 `**kwargs` 传给 Playwright |
| playwright | 1.64.0 | 与 cloakbrowser 0.6.3 配套。0.6.2 起包含对 Playwright 1.64 的修正 |
| curl_cffi | 0.16.3 | Cookie 刷新用，提供 aarch64 wheel。0.16.4 仍是 beta，不采用 |

免费档二进制按平台区分：amd64 是 `146.0.7680.177.5`，arm64 是 `146.0.7680.177.3`。这是 0.6.3 自带的平台版本，不是构建脚本选错架构。

## 配置

仓库根目录：

```bash
cp .env.oracle.example .env.oracle
openssl rand -hex 32
```

把新 token 写入 `.env.oracle` 的 `AISTUDIO_API_KEY`。把合并 job 打印的清单 digest 写入 `AISTUDIO_IMAGE`。`AISTUDIO_NOVNC_PUBLIC_URL` 只写远程画面站点根地址，不要带 `/vnc.html`。不要把旧机的私有代理地址写进 `AISTUDIO_PROXY`。

检查编排能解析，并且只发布回环端口：

```bash
docker compose --env-file .env.oracle -f docker/docker-compose.deploy.yml config
```

然后启动：

```bash
docker compose --env-file .env.oracle -f docker/docker-compose.deploy.yml up -d
```

账号卷是 `aistudio-oracle-data`，浏览器缓存卷是 `aistudio-oracle-browser-cache`。不要挂旧机的 `aistudio-api-data` 或 `aistudio-api-browser-cache`。重建容器时不要删这两个新卷。

宿主机内存和 CPU 上限故意没有写进编排。旧机的 `1800m` 不能当作三路生成已经验证过的配置。部署窗口先看浏览器实际占用，再决定是否加限制，并记录三路请求时的内存峰值、CPU、延迟和错误。

## Caddy

把 `docker/caddy/aistudio-oracle.caddy.example` 里的两个站点块并进现有 Caddy，替换占位域名。远程画面站点上的 `basic_auth` 没有路径匹配器，因此页面、静态资源和 WebSocket 握手都要经过它。不要为 `/websockify`、`*.js` 或 `*.html` 另写一条不认证的路由。

API 站点不要加 Basic Auth。Basic Auth 和 API 的 Bearer 都使用 `Authorization` 头，放在同一个站点会冲突。

在现有容器里生成密码哈希，替换示例里的哈希后再加载：

```bash
docker exec community-proxy caddy hash-password --plaintext 'CHOOSE-A-LONG-PASSWORD'
```

示例哈希是 `replace-this-password` 的 bcrypt（`$2b$`，cost 14），只为了让示例本身是合法哈希。加载前必须换掉。

加载前先备份这次要改的 Caddy 配置，并先执行 Caddy 自己的配置校验。校验通过后再让现有进程加载新站点。

## 登录

1. 用 API 密钥打开 `https://API_DOMAIN:8443`。
2. 账号管理里点现有的「登录账号」。
3. 点「打开远程画面」。浏览器会先要 Caddy 的 Basic Auth，通过后才是 noVNC。
4. 在 Google 页面完成登录和验证。同一时间只能有一个登录会话。
5. 关掉 noVNC 页面不会取消登录。要取消就用后台的取消按钮。
6. 登录成功后画面变黑是临时登录浏览器已关闭，工作浏览器仍以无头方式运行。

没有设置公网地址时，后台仍给出 `http://127.0.0.1:6080/vnc.html?autoconnect=1&resize=scale`，这时才需要 SSH 隧道。茶话会这次部署不使用那条路径。

## 并发

编排把 `AISTUDIO_MAX_CONCURRENCY` 固定为 `3`。三个请求可以同时拿到 `asyncio.Semaphore(3)` 的许可；三个都占用时，第四个在 `require_busy_lock()` 处返回 429。

浏览器对象仍只在 `BrowserSession` 的一个线程上使用。同步 Playwright 不能把 `max_workers` 改成 3 后跨线程共享同一个页面。重叠发生在页面里：每个请求用自己的 `rid` 发起一个 XHR，浏览器线程只负责启动和短轮询，不再把整个流式回复占满到上游结束。因此后两个请求不用等第一个上游结束才能发出。取消或超时只中止对应的 `rid`，并在生成器结束后释放信号量名额。

单测用假页面覆盖了四件事：三个请求都在任一结束前启动上游、分片不串线、取消一个不会停掉另外两个、超时后信号量可以再次获取。这还不是目标机上的真实 Google 请求。部署窗口仍要看到三路上游时间重叠，以及那时的内存、CPU、延迟和错误。单次登录会话仍是 1 个，和生成并发无关。

## 部署窗口还要做的事

本说明写完时，生产机器、DNS 和线上 Caddy 都还没有被这个改动触碰。合并到 master 之后才会推送多架构镜像。在那之前没有可固定的清单 digest。

目标机上仍需核实：ARM64 容器里的浏览器能否启动，公网 Basic Auth 是否挡住未认证的页面和 WebSocket，Google 登录和真实流式回复，三路重叠时的资源峰值，以及重启后账号卷是否还在。镜像构建、`/health` 和页面能打开都不能代替这些验收。
