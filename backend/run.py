#!/usr/bin/env python3
# ============================================================
# 城市公共设施智能报修与派单系统 - 后端启动入口
# 作用：通过 uvicorn 启动 FastAPI 应用，配置热重载和端口
# 启动命令：python run.py  或  uvicorn app.main:app --reload --port 8000
# ============================================================

import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,       # 开发环境热重载
        log_level="info",
    )
