# 部署上线指南

城市公共设施智能报修与派单系统 —— 生产环境部署手册。

本指南基于 Docker Compose 单机部署（最常用、最快上线）。文末给出横向扩展 / K8s 的演进方向。

> **两套编排，按机器配置选择：**
> - **`docker-compose.lite.yml`** → **2核4G / 无域名（IP 直连）**，已做内存压缩，**你当前的场景用这个**。见下方【§0 低配·无域名快速部署】。
> - `docker-compose.prod.yml` → 4核8G 及以上 / 有域名走 HTTPS，见 §2 起的标准章节。

---

## 0. 低配·无域名快速部署（2核4G + 公网 IP 直连）

如果你的服务器只有 **2核4G**、且**没有域名**，按本章操作即可跑起来。

### 0.1 能做到什么、做不到什么（先看清楚）

| 端 | 无域名 IP 直连能否使用 |
|----|----------------------|
| 市政管理 PC 后台 | ✅ 浏览器直接 `http://公网IP/admin/` 可用 |
| 维修员移动 H5 | ✅ 手机浏览器 `http://公网IP/worker/` 可用（页面内定位/拍照正常） |
| 市民微信小程序 | ⚠️ **正式发布不行**。微信小程序正式版强制「HTTPS + 已备案域名」，IP 和 http 都无法配置为合法服务器域名。**仅能在微信开发者工具里勾选「不校验合法域名」做联调测试。** 要正式上线市民端，必须后续补一个备案域名 + HTTPS。 |
| 一键登录（阿里云号码认证） | ⚠️ 依赖 https 与签名，http 测试环境可能受限，建议有域名后再开。 |

> 结论：**2核4G + 无域名适合演示、验收、内部测试、PC/H5 端试用**；市民小程序正式上线仍需域名。

### 0.2 第一步：加 2G swap（务必先做）

4G 内存跑 7 个容器偏紧，不加 swap 在构建或高峰期容易被 OOM Killer 杀进程：

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
# 开机自动挂载
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h    # 确认 Swap 行显示 2.0G
```

### 0.3 第二步：镜像不要在小机器上构建（关键省时省力）

前端三端 Vite 构建峰值内存 >1.5G，2C4G 上 `docker build` 极易卡死或 OOM。**推荐在你的开发机（当前这台 Windows/或任何 ≥8G 内存的机器）构建好镜像，导出后传到服务器加载：**

在**开发机**（项目根目录）：

```bash
# 构建两个镜像
docker compose -f docker-compose.lite.yml build

# 导出为离线包
docker save city-repair/backend:latest city-repair/frontend:latest -o city-repair-images.tar

# 连同编排与环境变量一起传到服务器
scp city-repair-images.tar docker-compose.lite.yml .env.production root@<服务器公网IP>:/opt/city_repair/
```

> 若开发机没有 Docker、只能在服务器上构建：先确保 0.2 的 swap 已生效，构建时临时停掉其它占内存进程，并接受构建较慢（可能 15-30 分钟）。

在**服务器**：

```bash
cd /opt/city_repair
docker load -i city-repair-images.tar   # 载入镜像
```

### 0.4 第三步：配置环境变量并启动

```bash
cd /opt/city_repair
cp .env.production.example .env.production
vi .env.production     # 填强密码；LLM/OSS/高德密钥可先留空（相关AI功能不可用，主流程可跑）
```

启动（lite 编排里 frontend 直接占用服务器 **80 端口**）：

```bash
docker compose --env-file .env.production -f docker-compose.lite.yml up -d --no-build
# 若镜像就是在本机构建的，去掉 --no-build
docker compose -f docker-compose.lite.yml ps     # 等待全部 healthy
```

初始化数据库：

```bash
docker compose -f docker-compose.lite.yml exec backend python scripts/init_db.py
# 演示/测试可灌模拟数据（生产勿用）：
# docker compose -f docker-compose.lite.yml exec backend python seed_data.py
```

### 0.5 访问方式（IP 直连）

云控制台**安全组放行 80 端口**（TCP），然后：

| 端 | 地址 |
|----|------|
| 市民端 | `http://<公网IP>/` |
| 维修员 H5 | `http://<公网IP>/worker/` |
| 管理后台 | `http://<公网IP>/admin/` |
| 后端健康检查 | 服务器内执行 `curl http://127.0.0.1:8000/health`（8000 仅绑本机，不对公网开放） |

> 前端请求的是相对路径 `/api/v1/...`，由 Nginx 反代到后端容器，**无需配置跨域或改前端地址**，换成 IP 就能用。

### 0.6 4G 内存的运行注意

- lite 编排已给每个容器设了 `mem_limit`（ES 堆 384M、MySQL buffer pool 256M、Mongo cache 256M、Redis maxmemory 128M），**不要随意调大**。
- 用 `docker stats` 观察内存；若某容器频繁被 OOM 重启，优先把 ES 堆降到 256m（改 `ES_JAVA_OPTS=-Xms256m -Xmx256m`）。
- 数据量小、并发低时 2C4G 可流畅跑演示；**真实生产/多人并发建议升到 4核8G** 并换用 `docker-compose.prod.yml`。
- 备份、更新发布、后台任务拆分扩容等操作与标准版一致，见 §8、§9、§10。

---

## 1. 架构与组件

| 层 | 组件 | 说明 |
|----|------|------|
| 接入层 | Nginx（frontend 容器） | 托管三端静态文件，反代 `/api` 到后端 |
| 应用层 | FastAPI / uvicorn（backend 容器） | API + **内嵌** RabbitMQ 消费者、ES 同步消费者、自动完结工单调度器 |
| 数据层 | MySQL 8.4 / Redis 7.4 / MongoDB 6 / Elasticsearch 8.12 | 四库分层 |
| 消息 | RabbitMQ 3.12 | 派单队列、超时延迟队列、ES 同步队列 |
| 外部服务 | 阿里云百炼 LLM、阿里云 OSS、阿里云号码认证、高德地图 | 需自备密钥 |

**三端访问路径（同一域名）：**
- 市民端：`https://域名/`
- 维修员端：`https://域名/worker/`
- 管理后台：`https://域名/admin/`
- API：`https://域名/api/v1/...`，接口文档 `https://域名/api/docs`（见 §7 建议生产关闭）

> ⚠️ **关键约束：backend 只能单副本。** MQ 消费者、ES 同步、定时调度器都写在 FastAPI 的 `lifespan` 里，随进程启动。若起多个副本，会**重复消费消息、重复派单**。扩容前必须先拆分后台任务（见 §10）。

---

## 2. 服务器要求

- **操作系统**：Linux（Ubuntu 22.04 / CentOS 7+ 等），国内云主机建议阿里云/腾讯云。
- **配置**：最低 **4 核 8G**，推荐 **8 核 16G**（ES 单节点默认给了 1G 堆，MySQL/Redis/Mongo/RabbitMQ 同机）。
- **磁盘**：≥ 50G，建议挂载独立数据盘。
- **软件**：Docker 24+ 与 Docker Compose v2（`docker compose` 命令）。
- **网络**：开放安全组 **80、443**；数据库端口**不要**对公网开放。

安装 Docker（以 root 执行）：

```bash
# 官方脚本（国内可用阿里云镜像源安装 docker-ce）
curl -fsSL https://get.docker.com | bash
systemctl enable --now docker
docker --version && docker compose version
```

---

## 3. 上线前准备的第三方密钥

在 `.env.production` 中填写（详见模板 `.env.production.example`）：

1. **阿里云百炼（LLM）**：开通 DashScope，创建 `sk-` 开头的 API Key。用于工单 NLP 解析与 AI 验收图片对比，模型 `qwen-vl-max-latest`。
2. **阿里云 OSS**：创建 Bucket（建议与 ECS 同地域，用内网端点省流量），创建 RAM 子账号 AK/SK，授予该 Bucket 读写权限。
3. **阿里云号码认证**（一键登录，可选）：DypnsAPI 的 AK/SK。
4. **高德地图**：申请 Web 服务 Key（后端逆地理编码）与 JS API 安全密钥（前端 H5）。
5. **域名**：准备一个域名并解析到服务器公网 IP（用于 HTTPS）。

---

## 4. 部署步骤

```bash
# 1) 拉取/上传代码到服务器
git clone <你的仓库地址> /opt/city_repair
cd /opt/city_repair

# 2) 准备生产环境变量
cp .env.production.example .env.production
vi .env.production        # 逐项填写，所有 CHANGE_ME / YOUR_ 占位必须替换

# 3) 构建并启动全部服务（首次构建约 5-15 分钟）
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build

# 4) 查看启动状态，等待各容器 healthy
docker compose -f docker-compose.prod.yml ps
```

`backend` 的主机名（mysql/redis/...）已在 compose 里覆盖为内部服务名，`.env.production` 里即使写的是服务名也无需改动。

---

## 5. 初始化数据库与数据

基础设施就绪后，在 backend 容器内执行初始化：

```bash
# 初始化 MySQL 表结构 / MongoDB / ES 索引
docker compose -f docker-compose.prod.yml exec backend python scripts/init_db.py

# （可选，仅演示/测试环境）填充模拟数据 —— 生产环境请勿执行
# docker compose -f docker-compose.prod.yml exec backend python seed_data.py

# （可选）把存量 MySQL 工单全量同步到 ES
docker compose -f docker-compose.prod.yml exec backend python scripts/sync_es.py
```

> 生产环境**不要**跑 `seed_data.py`，以免写入假工单/假结算。

---

## 6. 验证部署

```bash
# 后端健康检查
curl http://127.0.0.1:8000/health
# 期望：{"status":"ok","version":"3.0.0"}

# 通过 Nginx 访问前端与 API
curl -I http://127.0.0.1/            # 市民端
curl -I http://127.0.0.1/admin/      # 管理端
curl -I http://127.0.0.1/worker/     # 维修员端

# 看后端日志，确认消费者/调度器启动
docker compose -f docker-compose.prod.yml logs -f backend
# 应看到：RabbitMQ 派单消费者已启动 / ES Sync 消费者已启动 / 自动完结工单调度器已启动
```

浏览器打开 `http://服务器IP/`（域名未配 HTTPS 前）验证三端可登录、可提交工单。

---

## 7. 配置 HTTPS（强烈建议）

小程序 / H5 在生产环境要求 HTTPS。用宿主机 Nginx 或 Caddy 终结证书，反代到 frontend 容器。

**最简方案 —— Caddy 自动签证书：**

```bash
# 宿主机安装 caddy 后，新增 Caddyfile
你的域名 {
    reverse_proxy 127.0.0.1:8080
}
```
并把 `docker-compose.prod.yml` 里 frontend 端口改为 `"127.0.0.1:8080:80"`，`caddy run` 即可自动申请并续期 Let's Encrypt 证书。

**或宿主机 Nginx + certbot：** 用 `certbot --nginx` 签发证书，`server_name 你的域名; proxy_pass http://127.0.0.1:8080;`。

> 启用 HTTPS 后，后端已带 `--proxy-headers --forwarded-allow-ips=*`，能正确识别 `X-Forwarded-Proto`。
> 生产建议在反向代理层屏蔽 `/api/docs`、`/api/redoc`（仅限内网/办公网访问）。

---

## 8. 日常运维

```bash
# 查看日志
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend

# 重启某个服务
docker compose -f docker-compose.prod.yml restart backend

# 更新发布（重新构建并滚动重启）
git pull
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build

# 停止 / 启动
docker compose -f docker-compose.prod.yml down      # 停止（数据卷保留）
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
```

> §8、§9 的命令以 `docker-compose.prod.yml` 为例；**低配版把文件名换成 `docker-compose.lite.yml` 即可**，操作完全相同。

---

## 9. 数据备份

数据都在 Docker 命名卷里（`mysql_data / redis_data / mongo_data / es_data / rabbitmq_data`）。**重点备份 MySQL 与 MongoDB**：

```bash
# MySQL 逻辑备份（每日 cron）
docker compose -f docker-compose.prod.yml exec -T mysql \
  sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines city_repair' \
  | gzip > /data/backup/mysql_$(date +%F).sql.gz

# MongoDB 备份
docker compose -f docker-compose.prod.yml exec -T mongodb \
  mongodump --archive -u "$MONGO_USER" -p "$MONGO_PASSWORD" --authenticationDatabase admin \
  | gzip > /data/backup/mongo_$(date +%F).archive.gz
```

建议挂到独立数据盘 `/data/backup`，并同步到 OSS。Redis 已开 AOF，ES 数据可由 MySQL 经 `sync_es.py` 重建，不必单独备份。

---

## 10. 扩容与高可用演进（重要）

当前 backend 单进程同时承担「API + 后台消费者 + 定时任务」。要水平扩展 API，需先解耦：

1. **拆分后台任务为独立进程**：把 `_start_dispatch_consumer`、`_start_es_sync_consumer`、`_start_auto_close_scheduler` 从 `app/main.py` 的 `lifespan` 中抽出，做成独立入口（如 `python -m app.workers.dispatch_worker`），用环境变量控制「API 进程不启动消费者 / worker 进程不监听 HTTP」。
2. 拆分后即可：`backend`（API）多副本 + Nginx/负载均衡轮询；`worker`（消费者）按需扩副本（MQ 多消费者天然支持竞争消费，不重复）。
3. 数据层高可用：MySQL 主从、Redis Sentinel/Cluster、ES 三节点、RabbitMQ 镜像队列；或直接改用云数据库 RDS / 云 Redis / 托管 ES / 托管 RabbitMQ，把 compose 里的基础设施替换为云服务连接串即可（改 `.env.production` 的主机名即可，无需改代码）。
4. 容器编排可迁移到 K8s：Deployment（API 多副本）+ CronJob（自动完结）+ StatefulSet/云数据库。

---

## 11. 安全检查清单（上线前逐项确认）

- [ ] `.env.production` 所有 `CHANGE_ME` / `YOUR_` 占位已替换为**强密码/真实密钥**
- [ ] `DEBUG=false`
- [ ] `SECRET_KEY`、`JWT_SECRET_KEY` 为随机长串（`openssl rand -hex 32` 生成）
- [ ] 数据库/Redis/Mongo/ES/RabbitMQ 端口**未**对公网开放（compose 已不发布，勿额外加 ports）
- [ ] 正式上线市民小程序需 HTTPS + 备案域名；**无域名/仅 IP 时只可用于演示与 PC/H5 测试**（见 §0.1）
- [ ] 生产环境未执行 `seed_data.py`
- [ ] OSS RAM 账号仅授予目标 Bucket 最小权限
- [ ] CORS 已按需收紧（代码现为 `allow_origins=["*"]`，正式环境建议改为具体域名/IP）
- [ ] 已配置每日备份并验证可恢复
- [ ] 2核4G 机器已配置 2G swap（见 §0.2）

---

## 附：部署文件清单

| 文件 | 作用 |
|------|------|
| **`docker-compose.lite.yml`** | **2核4G / 无域名低配编排**（内存压缩 + mem_limit，frontend 直占 80） |
| `docker-compose.prod.yml` | 标准生产编排（4核8G+，内网隔离/健康检查/重启策略） |
| `.env.production.example` | 生产环境变量模板（两套编排共用） |
| `backend/Dockerfile` | 后端生产镜像（单 worker uvicorn + 健康检查） |
| `backend/.dockerignore` | 后端构建上下文排除 |
| `frontend/Dockerfile` | 三端多阶段构建到 Nginx |
| `frontend/nginx.conf` | 静态托管 + `/api` 反代 + SPA fallback |
| `frontend/.dockerignore` | 前端构建上下文排除 |
