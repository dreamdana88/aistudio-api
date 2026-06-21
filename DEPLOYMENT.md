# RackNerd + 1Panel 部署指南

本指南针对约 2 核、2.5 GB 内存的服务器，采用单实例、并发 1、域名 HTTPS 和手动更新。

## 1. 部署前准备

建议至少保留 10 GB 可用磁盘，并确认服务器具有约 2 GB Swap：

```bash
free -h
swapon --show
```

如果没有 Swap，可在服务器终端执行：

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

生成 API Token：

```bash
openssl rand -hex 32
```

不要把生成结果写入 GitHub、聊天记录或公开截图。

## 2. 在 1Panel 创建 Compose

在 1Panel 的容器编排中创建项目，将仓库里的以下文件放在同一项目目录：

- `docker-compose.deploy.yml`
- `config.yaml`

Compose 环境变量至少填写：

```dotenv
AISTUDIO_API_KEY=刚才生成的随机Token
AISTUDIO_IMAGE=ghcr.io/dreamdana88/aistudio-api:latest
AISTUDIO_BIND_PORT=8080
AISTUDIO_MAX_CONCURRENCY=1
```

使用 `docker-compose.deploy.yml` 启动。服务只监听
`127.0.0.1:8080`，不会直接暴露到公网。

首次启动会将 CloakBrowser 下载到独立持久卷。账号数据使用
`aistudio-api-data`，浏览器缓存使用 `aistudio-api-browser-cache`；
重建容器不会删除这两个卷。

## 3. 域名与 HTTPS

在 1Panel 创建反向代理网站：

- 上游地址：`http://127.0.0.1:8080`
- 启用 HTTPS 并申请证书
- 强制跳转 HTTPS

为流式响应设置较长超时并关闭代理缓冲。Nginx 高级配置可加入：

```nginx
proxy_http_version 1.1;
proxy_buffering off;
proxy_cache off;
proxy_read_timeout 600s;
proxy_send_timeout 600s;
client_max_body_size 50m;
```

访问域名后输入 `AISTUDIO_API_KEY`，再通过后台导入 Cookies。不要上传本地
`data/accounts`，也不要把 Cookie 发给其他人。

## 4. 验收

```bash
curl https://你的域名/health
curl https://你的域名/v1/models \
  -H "Authorization: Bearer 你的Token"
```

`/health` 应返回 `status: ok`；受保护接口在没有 Token 时应返回 401。
随后在 SillyTavern 中使用 `https://你的域名/v1` 和同一 Token 测试流式对话。

## 5. 更新与回退

推荐固定版本，而不是长期依赖 `latest`：

```dotenv
AISTUDIO_IMAGE=ghcr.io/dreamdana88/aistudio-api:1.0.0
```

更新前，先在 1Panel 中备份名为 `aistudio-api-data` 的卷。然后修改镜像标签、
拉取镜像并重建编排。不要勾选删除持久卷。

如果新版本异常，把 `AISTUDIO_IMAGE` 改回上一个版本并再次重建。账号数据和
浏览器缓存位于独立卷中，不会随镜像回退而丢失。

## 6. 资源建议

默认配置限制容器使用约 1.8 GB 内存、1.75 核 CPU、512 MB `/dev/shm`，
并将并发设为 1。稳定运行一段时间后可以尝试并发 2；若出现浏览器退出、
响应超时或 OOM，应立即恢复为 1。

## 风险说明

本项目依赖非官方网页兼容流程。Google 页面、BotGuard、账号验证或服务条款
变化均可能导致服务失效；机房 IP 也可能触发额外登录验证。请自行评估账号和
使用风险，不要将其视为具有 SLA 的生产服务。
