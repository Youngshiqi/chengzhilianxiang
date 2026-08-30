# ============================================================
# 城市公共设施智能报修与派单系统 - 前端生产镜像（三端合一）
# 多阶段构建：Node 构建三端 Vite 产物 -> Nginx 托管静态文件 + 反代后端
#   市民端 citizen-app : 根路径   /
#   管理端 admin-pc    : /admin/
#   维修员 worker-h5   : /worker/
# 三端 API 均走相对路径 /api/v1，由 Nginx 统一反代到 backend 容器。
# 构建上下文为 frontend/ 目录。
# ============================================================

# ---------- Stage 1: 构建三端静态产物 ----------
FROM node:20-alpine AS builder
WORKDIR /build

# 先拷贝各端依赖清单，充分利用层缓存
COPY citizen-app/package*.json ./citizen-app/
COPY worker-h5/package*.json  ./worker-h5/
COPY admin-pc/package*.json   ./admin-pc/

RUN cd citizen-app && npm ci || npm install
RUN cd worker-h5  && npm ci || npm install
RUN cd admin-pc   && npm ci || npm install

# 拷贝全部源码并构建（子路径应用通过 --base 指定资源前缀，无需改源码）
COPY . .
RUN cd citizen-app && npx vite build
RUN cd worker-h5  && npx vite build --base=/worker/
RUN cd admin-pc   && npx vite build --base=/admin/

# ---------- Stage 2: Nginx 托管 ----------
FROM nginx:1.27-alpine AS runtime

# 清空默认站点，放入三端产物
RUN rm -rf /usr/share/nginx/html/*
COPY --from=builder /build/citizen-app/dist /usr/share/nginx/html/
COPY --from=builder /build/admin-pc/dist   /usr/share/nginx/html/admin/
COPY --from=builder /build/worker-h5/dist  /usr/share/nginx/html/worker/

# Nginx 站点配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
