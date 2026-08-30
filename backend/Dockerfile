# ============================================================
# 城市公共设施智能报修与派单系统 - 后端生产镜像
# 基础镜像：python 3.12-slim（FastAPI + uvicorn）
# 注意：应用在 lifespan 内启动了 RabbitMQ 消费者 / ES 同步 / 自动完结调度器，
#       因此生产必须【单进程单 worker】运行，多副本会导致消息重复消费。
#       需要扩容时请先把后台任务拆分为独立 worker 进程（见部署文档）。
# ============================================================
FROM python:3.12-slim AS base

# 避免 .pyc、缓冲输出，保证日志实时可见
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Shanghai

# 系统依赖：Pillow 运行所需的图像库；curl 用于健康检查
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libjpeg62-turbo zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先单独安装依赖，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install -r requirements.txt

# 拷贝应用代码（scripts / seed_*.py 一并拷入，便于容器内初始化与补数据）
COPY . .

EXPOSE 8000

# 健康检查：命中 FastAPI 的 /health 接口
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fs http://127.0.0.1:8000/health || exit 1

# 生产启动：关闭 reload；单 worker；由 docker-compose 控制并发副本数=1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*", \
     "--log-level", "info"]
