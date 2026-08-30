# 城市公共设施智能报修与派单系统

## 项目概述

面向政府市政部门的公共设施报修-派单-维修-验收-结算-数据分析全闭环AI智能管理系统。依托轻量化AI编排（Dify）、消息队列（RabbitMQ）、空间算力（Redis Geo）技术，打通市民、一线维修员、市政管理员、财政部门四方信息壁垒。

## 技术架构

- **前端**: Vue 3 + Element Plus（市民微信小程序 / 维修员移动H5 / 市政管理PC后台）
- **API网关**: FastAPI（异步非阻塞、自动OpenAPI文档、Pydantic强校验）
- **AI引擎**: Dify（可视化编排NLP解析、派单评分、AI验收三大工作流）
- **数据存储**: MySQL + Redis + MongoDB + Elasticsearch 四库分层架构
- **消息队列**: RabbitMQ（派单队列、延迟超时队列、差评复核队列）

## 四库存储职责

| 存储组件 | 职责定位 |
|---------|---------|
| MySQL 8.0 | 结构化关系型核心业务数据（用户、工单、设施、结算），强事务保障 |
| Redis 7 | 热点缓存、Geo空间派单、分布式锁、实时计数器、在岗集合维护 |
| MongoDB 6 | 半结构化文档（AI解析JSON、维修记录、图片元数据、审计日志） |
| Elasticsearch 8 | 全文检索、IK中文分词、聚合统计分析、数据驾驶舱 |

## 快速启动

```bash
# 1. 启动所有基础设施
docker-compose up -d

# 2. 初始化数据库
cd backend && python scripts/init_db.py

# 3. 填充模拟数据
python seed_data.py

# 4. 启动后端
python run.py

# 5. 启动前端（三端分别启动）
cd frontend/citizen-app && npm install && npm run dev
cd frontend/worker-h5 && npm install && npm run dev
cd frontend/admin-pc && npm install && npm run dev
```

## 项目边界

- V3.0 纳入范围：四库分层存储、三端前端、三大AI工作流、RabbitMQ异步队列
- 明确排除：IoT设备对接、AI预测性运维、政务财务系统对接、原生APP开发
