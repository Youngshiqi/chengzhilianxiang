# 城市公共设施智能报修与派单系统
## 产品需求文档（PRD）v3.3
### 数据存储升级版：MySQL + Redis + MongoDB + Elasticsearch 四库分层架构

文档版本：v3.3　　　最后更新：2026-06-25
编制人：项目负责人　　审核人：政务技术模拟审核人
适用场景：计算机应届生毕业设计 / 后端面试项目 / 课程设计归档
阅读对象：答辩评委、面试官、项目开发人员

---

## 修订说明

| 版本号 | 修订核心内容 | 修订日期 |
|--------|------------|----------|
| v1.0 | 初稿，完成痛点、需求、业务、架构、规则基础梳理 | 2026-06-18 |
| v2.0 | 新增用户故事、标准接口、数据模型、异常流程；优化业务流程图、Redis/ES配置、非功能需求、项目边界，全文格式标准化 | 2026-06-20 |
| v3.0 | 数据存储架构全面升级：引入 MySQL + Redis + MongoDB + Elasticsearch 四库分层存储架构，重构数据模型设计与各模块存储分工，补充 MongoDB 文档模型规范 | 2026-06-21 |
| v3.1 | 更新 OSS 为北京地域实际配置（city-repair-system-images），补全图片上传链路（前端 FormData → 服务端 oss2 SDK 直传 → 公网 URL 返回），移除 STS 预签名方案，更新技术选型表与数据流转图 | 2026-06-24 |
| v3.2 | 与代码实现全面同步：补充实际 API 路由清单（含登录/注册/位置上报/到场签到/绩效查询等）、修正驾驶舱数据源描述（MySQL 聚合而非 Redis counter:today）、修正维修员在线集合 Key 名称（workers:online 替代 dispatch:online_workers）、补充 ES Sync RabbitMQ 可靠异步投递架构（含 DLQ 死信队列+指数退避重试）、补充高德驾车距离修正与三级定位降级策略、补充 citizen_confirm / auto_close_expired_tickets 业务闭环 | 2026-06-24 |
| v3.3 | 登录方案调整：微信授权登录 → 短信验证码登录（腾讯云短信SDK）；通信方案调整：WebSocket双向通信 → HTTP单向轮询；更新架构图、接口规范、数据模型、Redis Key、术语表 | 2026-06-25 |

---

## 一、项目概述

### 1.1 项目定位
面向政府市政部门的公共设施报修－派单－维修－验收－结算－数据分析全闭环AI智能管理系统，依托轻量化AI编排、消息队列、空间算力技术，打通市民、一线维修员、市政管理员、财政部门四方信息壁垒，解决传统人工工单低效、派单盲目、数据缺失、运维成本高的行业痛点，打造轻量化智慧城市运维共治平台。

### 1.2 四方目标用户及核心价值

| 用户角色 | 核心痛点 | 系统核心价值 |
|----------|---------|-------------|
| 市民（C端小程序） | 报修渠道繁琐、位置描述困难、维修进度不可查 | 3步极简报修，进度可视化，降低群众报修成本 |
| 维修员（B端H5） | 被动等单、跨区返工、维修无参考、绩效不透明 | AI智能派单、最优路线规划、知识库赋能、绩效自动核算 |
| 市政管理员（G端后台） | 工单管控难、应急调度慢、运维数据碎片化 | GIS设施一张图、人工干预调度、可视化数据驾驶舱 |
| 财政部门（G端后台） | 经费核算粗放、维修费用无法溯源、审计风险高 | 标准化自动结算、全流程操作留痕，满足政务审计合规 |

### 1.3 项目三大核心目标
- **效率目标**：维修员日均工单处理量提升40%，工单平均响应时长压缩至15分钟以内
- **业务目标**：市政公共设施完好率由85%提升至94%，市民服务综合满意度≥90分
- **落地目标**：适配应届生毕设开发体量，核心功能可演示、代码可一键部署、业务数据可模拟、技术亮点可面试深挖

### 1.4 技术栈及选型理由

| 技术组件 | 分层归属 | 选型核心理由 | 应届生适配优势 |
|----------|---------|-------------|--------------|
| Vue 3 + Element Plus | 前端层 | 政务系统组件适配度高、权限组件成熟、UI合规统一 | 生态完善、开源组件多、开发上手快 |
| FastAPI | API网关层 | 异步非阻塞高并发、自带OpenAPI文档、Pydantic强校验 | 代码简洁、Python语法易懂、调试成本低 |
| Dify | AI引擎层 | 可视化编排AI能力，无需自研训练底层大模型 | 零代码对接NLP/OCR/视觉能力，快速落地AI亮点 |
| 阿里云 OSS（北京地域） | 对象存储层 | 存储工单现场照片、维修前后对比图等静态文件，按日期分目录，公网 CDN 加速访问 | oss2 Python SDK 服务端直传；Bucket 公共读，按 tickets/YYYY/MM/DD/{uuid}.ext 组织 |
| MySQL 8.0 | 持久化层（关系型） | 存储用户、工单、权限、结算等结构化核心业务数据，事务保障数据一致性 | SQL体系完善、事务支持完备、面试高频 |
| Redis 7 | 缓存 & 计算层 | 工单状态热缓存、Geo空间派单、分布式锁、实时计数器、全局热配置 | 面试高频中间件，核心用法简单易掌握 |
| MongoDB 6 | 文档存储层 | 存储报修图片元数据、AI解析结果、维修记录附件、审计操作日志等半结构化/非结构化文档 | Schema灵活、天然适配AI输出JSON结构 |
| Elasticsearch 8 | 检索 & 聚合层 | 工单全文检索、故障聚合统计、设施档案检索、绩效数据分析大盘 | 仅需掌握基础聚合语法，满足毕设数据可视化 |
| RabbitMQ | 消息调度层 | 业务解耦、异步工单处理、超时延迟兜底、ES同步可靠投递（含DLQ死信+指数退避重试） | 队列逻辑清晰，可演示异步业务核心流程 |

---

## 二、项目背景与痛点分析

### 2.1 全参与方业务痛点对照表

| 参与方 | 现存核心痛点 | 直接业务后果 |
|--------|------------|------------|
| 市民 | 设施故障无专属报修入口；12345人工报备位置成本高；维修进度无公示 | 群众投诉率居高不下，政务服务口碑受损 |
| 维修班组 | 线下人工等单、纸质工单易丢失；同片区故障拆分派单；台账手写归档 | 人员日均工单量低，跨片区出勤燃油、人力成本浪费严重 |
| 市政管理部门 | 运维数据零散无汇总；故障高发品类、路段无统计；满意度抽样统计失真 | 年度预算编制盲目，无法数据化向上级汇报运维成果 |
| 财政部门 | 运维经费逐年递增，但设施完好率无提升；紧急抢修费用管控缺失 | 政务审计压力大，运维管理漏洞无法排查溯源 |

### 2.2 政策驱动依据
国家发改委《深化智慧城市发展推进全域数字化转型行动计划》（2026年3月正式印发）明确三项硬性要求：
1. 全域推进市政公共设施数字化建档、智能化闭环运营管理
2. 搭建群众参与、评价联动的便民运维评价体系
3. 打通城管、电力、燃气、交通跨部门工单协同通道

结论：项目贴合最新政务数字化政策，具备官方预算、考核刚需，不属于虚构毕设伪需求。

---

## 三、三方用户需求拆解（含用户故事 + 验收标准）

### 3.1 市民端小程序（C端）

#### 3.1.1 用户故事清单

| 故事ID | 标准化用户故事 | 量化验收标准 |
|--------|-------------|------------|
| US-C01 | 作为普通市民，我想要拍照/扫码/文字多渠道报修，快速上报道路设施故障 | GPS自动地址反查准确率≥90%；离线可存报修草稿；3步内完成工单提交，提交3s内返回专属工单号 |
| US-C02 | 作为报修市民，我想要实时查看维修进度，避免报修后无音讯 | 工单状态变更后HTTP轮询获取最新进度；进度页含时间轴+脱敏维修员位置；支持历史工单筛选查询 |
| US-C03 | 作为市民，我想要评价维修服务，反馈服务好坏 | 支持星级+标签+文字评价；2星及以下差评自动触发管理员复核；评价数据联动维修员绩效台账 |

#### 3.1.2 功能优先级清单

| 功能名称 | 优先级 | 核心技术要点 | 业务边界说明 |
|----------|-------|------------|------------|
| 短信验证码登录 | P0 | 腾讯云短信SDK、JWT鉴权、手机号脱敏 | 仅采集手机号、昵称；手机号脱敏写MySQL users表 |
| 多渠道快速报修 | P0 | NLP文本解析、OCR图片识别、AI故障置信度判定 | 工单主表写MySQL；AI解析JSON写MongoDB；报修图片元数据写MongoDB |
| 工单进度可视化查询 | P0 | HTTP轮询查询、Leaflet免费地图渲染、Redis缓存 | 维修员位置脱敏展示；Redis ticket缓存热读，Miss降级MySQL |
| 服务评价管理 | P1 | RabbitMQ差评复核延迟队列、MySQL evaluations写入 | 工单完结后方可评价；差评触发MQ延迟队列复核 |
| 报修积分激励 | P2 | Redis积分计数、MySQL规则配置 | Redis INCR原子操作积分；仅模拟兑换流程，不对接支付 |

### 3.2 维修员移动端H5（B端）

#### 3.2.1 用户故事清单

| 故事ID | 标准化用户故事 | 量化验收标准 |
|--------|-------------|------------|
| US-W01 | 作为一线维修员，我想要实时接收工单推送，不用线下定点等待派单 | 工单大厅支持按距离排序；5分钟未接单自动释放派单权限流转下一维修员 |
| US-W02 | 作为维修员，我想要系统规划最优行驶路线，减少多点往返返工 | 高德驾车距离修正Redis Geo直线距离；支持多工单合并规划路径 |
| US-W03 | 作为维修员，我想要上传维修前后照片闭环工单，留存工作凭证规避追责 | 照片元数据写MongoDB；AI视觉核验结果写MongoDB ai_analysis_logs |

#### 3.2.2 功能优先级清单

| 功能名称 | 优先级 | 核心技术要点 | 业务边界说明 |
|----------|-------|------------|------------|
| 实时工单接单大厅 | P0 | HTTP GET 查询 + Redis Geo 距离排序 + 高德驾车距离修正 | 仅适配移动端H5；Redis维护在线维修员集合 workers:online |
| 工单导航+设施档案查看 | P0 | 高德开放API、URL Scheme跳转、ES facilities_index检索 | ES检索设施档案；Redis Geo计算维修员到设施距离 |
| AI智能维修知识库 | P1 | Dify故障方案推荐、ES历史维修案例检索 | ES tickets_index全文检索历史同类工单；Dify推荐方案写MongoDB ai_analysis_logs |
| 个人绩效自动统计 | P1 | Redis worker:{id}:daily_order 计数；MySQL 历史工单统计 | Redis worker:{id}:daily_order 实时计数；ES workers_perf_index 多维聚合绩效 |

### 3.3 市政管理后台（G端）

#### 3.3.1 用户故事清单

| 故事ID | 标准化用户故事 | 量化验收标准 |
|--------|-------------|------------|
| US-M01 | 作为市政管理员，我想要地图全域查看设施状态，把控城市运维全局态势 | GIS三色标注设施状态；支持设施类型筛选；Redis Geo实时维修员点位；ES检索设施故障历史 |
| US-M02 | 作为调度管理员，我想要手动干预工单，处置紧急滞留工单 | 支持强制指派、暂停派单、释放工单锁；所有操作写MongoDB audit_logs全量留痕 |
| US-M03 | 作为运维负责人，我想要导出可视化报表，快速完成年度运维汇报 | ES Aggregation驾驶舱；MySQL结算数据导出PDF/Excel；MongoDB审计日志查询 |

#### 3.3.2 功能优先级清单

| 功能名称 | 优先级 | 核心技术要点 | 业务边界说明 |
|----------|-------|------------|------------|
| GIS设施一张图调度台 | P0 | 高德地图JS API + Redis Geo空间坐标 + ES geo_point查询 | 系统内置1000条模拟市政设施点位；Redis Geo维修员实时位置 |
| 工单人工调度干预 | P0 | Redis分布式锁强制释放、RabbitMQ工单重投递、MongoDB审计 | 强制指派操作写MongoDB audit_logs；Redis lock强制释放 |
| 运维数据驾驶舱 | P1 | MySQL聚合统计 + ES Aggregation + ECharts可视化 | MySQL实时指标+ES历史聚合双层数据源；仅做复盘，不做预测 |
| 运维费用结算管理 | P1 | MySQL结算单、MongoDB审计日志、批量报表导出 | MySQL settlements自动生成；MongoDB audit_logs审计；不对接财务系统 |

---

## 四、四大核心业务场景说明

### 4.1 场景一：市民AI智能报修流程

核心规则：文字描述为必填核验项，拍照为辅助增强项；夜间黑屏、异响、间歇性故障依托文字兜底核验，AI双向校验文本+图片信息。

数据存储分工：
- 市民报修信息 → MySQL tickets主表落地，工单ID生成后立即返回受理回执
- 逆地理编码 → 高德 API GPS → 结构化地址（district冗余存储，支持三级降级：GPS → IP定位 → 默认长沙中心）
- Dify NLP解析JSON结果 → MongoDB ai_analysis_logs异步写入，不阻塞主流程
- 报修图片元数据（OSS URL、GPS、时间戳）→ MongoDB ticket_attachments
- 工单热状态缓存 → Redis ticket:{tid}:info，14天TTL
- 重复工单检测 → ES tickets_index查重，7天内同点位未完结工单合并
- 工单入队 → RabbitMQ dispatch队列，异步触发派单流程
- ES 同步 → RabbitMQ es_sync 队列（可靠异步投递，消费者全量加载 MySQL → ES，含指数退避重试 + DLQ 死信）

### 4.2 场景二：多因子AI智能派单流程（系统核心亮点）

派单底层逻辑：摒弃单纯就近派单，以「最小运维总成本」为目标，综合响应时效、人力负载、维修质量、风控成本多维评分，叠加硬性业务约束完成派单。

四库派单数据分工：
- 候选维修员过滤 → Redis workers:geo GEORADIUS 半径查询 + worker:{id}:daily_order 计数过滤
- 硬约束过滤 → MySQL workers 表查询（技能匹配/夜班时段/日单上限）
- 高德驾车距离修正 → 替换 Redis Geo 直线距离（缓存 5 分钟，降级保持直线距离）
- 多维评分决策 → Dify工作流（距离40% + 负载30% + 好评20% + 响应10%）；历史好评率从 ES workers_perf_index 读取；Dify不可用时降级为简单加权计算
- 派单锁定 → Redis分布式锁 lock:ticket:{tid} 固定300s过期，防并发双派
- 接单确认 → MySQL tickets.assigned_worker_id更新 + status → dispatching；Redis工单状态缓存同步
- 10分钟无人接单兜底 → RabbitMQ dispatch_timeout 延迟消息 → 自动升级强制指派，操作记入 MongoDB audit_logs
- 注：dispatch_timeout 使用 `x-delay` header，当前 exchange 为 DIRECT 类型，需要 rabbitmq_delayed_message_exchange 插件支持（已知限制）

### 4.3 场景三：维修全闭环 + AI验收核验流程

四库闭环数据分工：
- 维修员到场签到 → MongoDB repair_records 存 GPS 签到坐标（upsert 幂等）；MySQL tickets.started_at 更新
- 维修前现场照片 → MongoDB ticket_attachments（stage=report）
- 耗材录入 + 工时填报 → MongoDB repair_records（materials 数组灵活存储，无需 MySQL 多表 JOIN）
- 完工照片上传 → MongoDB ticket_attachments（stage=completion）
- Dify AI验收比对 → AI结果写MongoDB ai_analysis_logs；核验通过 → MySQL status → verifying；核验未通过 → status 保持 repairing（退回重做）
- 市民确认完工 → MySQL status → closed；触发结算自动生成（MySQL settlements）
- 7天超时自动完结 → 定时任务 auto_close_expired_tickets，status → closed 并触发结算
- 绩效结算触发 → MySQL settlements 自动生成，ES workers_perf_index 更新绩效指标

### 4.4 场景四：管理端数据驾驶舱统计流程

| 指标大类 | 细分指标 | 底层数据源 | 技术实现说明 |
|----------|---------|-----------|------------|
| 实时运营指标 | 今日新增/待派/处理中/验收中/完结工单量 + 在岗维修员 | MySQL 实时查询 + Redis workers:online SCARD | MySQL func.curdate() 查询今日数据；Redis SCARD 获取在岗人数 |
| 运维效率指标 | 工单平均响应时长、到场时长、完工时长 | MySQL 时间戳聚合 | 已完结工单的 created_at → closed_at 分钟差 AVG |
| 服务质量指标 | 综合好评率、差评工单台账 | MySQL evaluations + ES聚合 | ES terms/avg聚合，差评率阈值告警 |
| 故障分布指标 | 高频故障设施TOP10、故障高发路段统计 | MySQL 聚合查询（备用ES Aggregation） | GROUP BY facility_type，COUNT排序 |
| 人员绩效指标 | 维修员接单量、好评排行、平均响应速度 | Elasticsearch人员维度聚合 | workers_perf_index多维聚合，支持时段筛选 |
| 附件溯源查询 | 工单图片记录、AI核验结果溯源查询 | MongoDB ticket_attachments | 按ticket_id查询，展示AI核验JSON结果 |
| 环比趋势指标 | 近6个月月度工单统计 | MySQL DATE_FORMAT 分组统计 | 近6个月按月统计新增/完结工单 |

---

## 五、四库分层数据存储架构设计（核心升级）

### 5.1 四库存储职责总览

本系统采用 MySQL + Redis + MongoDB + Elasticsearch 四库分层存储架构，各库按数据特性分工，避免单一数据库承载过重压力，充分发挥各数据库核心优势。

| 存储组件 | 数据类型定位 | 负责存储内容 | 核心技术优势 |
|----------|------------|------------|------------|
| MySQL 8.0 | 结构化关系型数据 | 用户账号、工单主表、设施基础档案、维修员档案、权限角色、结算单据、评价记录、结算规则 | 强事务、外键约束、JOIN查询、数据一致性保障 |
| Redis 7 | 热点缓存 & 实时计算 | 工单状态缓存、派单分布式锁、维修员在线集合(workers:online)、Geo点位(workers:geo)、当日接单计数、热配置 | 毫秒级响应、Geo算力、过期自动清理、原子操作 |
| MongoDB 6 | 文档 & 非结构化数据 | 报修图片元数据、AI解析JSON结果、维修前后图片记录、操作审计日志、系统通知消息 | Schema灵活、天然存JSON、GridFS大文件、水平扩展 |
| 阿里云 OSS（北京地域） | 静态文件对象存储 | 工单现场照片、维修前后对比图、设施巡检图片等静态文件 | 按日期分目录组织，Bucket 公共读权限，服务端 oss2 SDK 直传，CDN 加速公网访问 |
| Elasticsearch 8 | 全文检索 & 聚合分析 | 工单全文检索索引、设施档案检索、绩效聚合统计、故障分布分析、数据驾驶舱大盘 | 倒排索引极速检索、Aggregation聚合分析、GeoPoint空间查询 |

### 5.2 端到端数据流转路径

以下描述核心业务节点的四库协作数据流：

| 业务节点 | 数据流转路径 |
|----------|------------|
| 报修提交 | FastAPI 接收图片 → oss2 上传至阿里云 OSS（北京地域）→ 返回公网 URL → 高德逆地理编码 → MySQL 写入工单主记录 → MongoDB 存储 AI 解析 JSON + 图片元数据 → Redis 缓存工单状态 → RabbitMQ 发布 dispatch 消息 + es_sync 消息 → ES Sync 消费者全量加载 MySQL → ES 索引 |
| 智能派单 | Redis workers:geo GEORADIUS 筛选候选维修员 → MySQL workers 表硬约束过滤 → 高德驾车距离修正 → Dify多维评分（降级为简单加权）→ Redis分布式锁锁定派单 → MySQL更新工单 assigned 字段 → Redis更新维修员计数 |
| 维修闭环 | MongoDB存维修前后图片元数据 + GPS签到记录 → Dify AI验收 → MySQL更新工单状态 → ES归档全量工单数据（via RabbitMQ es_sync 消费者）→ 触发结算自动生成 |
| 数据驾驶舱 | MySQL 实时查询（今日指标+聚合统计）→ Redis workers:online SCARD → ES Aggregation（备用聚合分析）→ MongoDB audit_logs 审计日志查询 |

### 5.3 MySQL 关系型数据库设计

职责定位：存储所有结构化、强一致性、需要事务保障的核心业务数据。外键约束保障引用完整性，事务保障工单状态变更一致性。

| 表名 | 用途说明 | 核心字段（简述） | 设计要点 |
|------|---------|---------------|---------|
| users | 用户账号表 | user_id, username, password_hash, phone, role, nickname, avatar_url, district, created_at, is_active | 存储市民/维修员/管理员三方账号基础信息，role字段控制RBAC权限（citizen/worker/admin）；市民通过手机号+短信验证码登录，phone字段作为唯一标识 |
| tickets | 工单主表 | ticket_id, user_id, facility_code, facility_type, district, status, description, address, location_lng, location_lat, emergency_level, assigned_worker_id, ai_category, ai_confidence, created_at, accepted_at, started_at, completed_at, closed_at | 工单全生命周期主记录，status枚举：pending/dispatching/repairing/verifying/closed；district冗余字段避免JOIN |
| facilities | 设施档案表 | facility_code, type, location_lng, location_lat, address, district, install_date, status, total_faults | 市政设施基础档案，1000条模拟点位，关联工单主表 |
| workers | 维修员档案表 | worker_id, name, skills(JSON), max_daily_orders, district, night_duty, star_rating, total_orders, avg_response_minutes, is_active | 维修员技能标签JSON字段，关联绩效与结算 |
| settlements | 结算单表 | settlement_id, ticket_id, worker_id, labor_cost, material_cost, total, audit_status, auditor_id, created_at | 自动生成结算单，全流程审计留痕，支持导出 |
| evaluations | 市民评价表 | eval_id, ticket_id, user_id, star, tags, comment, is_appealed, appeal_result, created_at | 联动维修员绩效，差评触发复核队列；ticket_id唯一索引防重复评价 |
| audit_rules | 结算规则配置表 | rule_id, facility_type, base_price, overtime_rate, emergency_multiplier, night_subsidy | 后台热配置结算规则，Redis读取缓存实时生效 |

索引优化要点：
- tickets表：status + created_at 联合索引（工单状态分页查询）
- tickets表：assigned_worker_id 索引（维修员工单快速查询）
- facilities表：location_lng + location_lat 组合索引（地理范围查询兜底）
- evaluations表：ticket_id 唯一索引（防重复评价）

### 5.4 Redis 缓存与实时计算设计

职责定位：承接热点数据缓存、毫秒级实时计算、Geo空间算力、分布式协调（锁/计数），是派单核心算力支撑层。

| Key Pattern | 类型 | 过期策略 | 业务用途说明 |
|-------------|------|---------|------------|
| worker:{id}:profile | Hash | 永久 | 维修员静态档案快速查：name/skills/max_daily/star_rating/avg_response_time/night_duty |
| worker:{id}:status | String | 永久覆盖 | 在线状态：online / busy / offline，派单过滤第一道门 |
| workers:geo | Geo | 5s刷新 | 维修员实时坐标集合，Geo半径查询候选维修员，GIS地图实时渲染 |
| workers:online | Set | 实时增减 | 当前在岗维修员ID集合，派单快速过滤，管理后台在岗人数统计 |
| worker:{id}:daily_order | String | 每日0点清零 | 当日工单计数，超过max_daily则过滤出候选队列 |
| lock:ticket:{tid} | String | 300s自动过期 | 工单派单分布式锁，防止并发双派，过期自动释放流转下一候选 |
| ticket:{tid}:info | Hash | 完结后7天过期（报修时14天） | 工单热点状态缓存：status/assigned_worker/updated_at，查询数据源 |
| config:dispatch_weights | Hash | 永久，热更新 | 派单权重配置：distance=40/load=30/rating=20/response=10，后台修改即时生效 |
| config:score_rules | Hash | 永久，热更新 | 积分规则、计价标准等全局热配置，修改无需重启服务 |
| counter:citizen:{uid}:points | String | 永久累加 | 市民积分计数器，INCR原子操作，积分兑换时CAS乐观锁 |
| settlement:month:{YYYYMM} | String | 60天 | 月度结算总额累加，INCRBYFLOAT |
| sms:{phone} | String | 300s | 短信验证码缓存，60s内禁止重复发送，5分钟过期 |
| amap:driving:{worker_id}:{ticket_id} | String | 300s | 高德驾车距离缓存，避免 force_dispatch 重复计费 |

Redis 与 MySQL 一致性保障：
- 工单状态变更采用「先写MySQL事务，再删Redis缓存，延迟500ms二次删除」策略防止脏读
- 维修员档案变更：后台更新MySQL workers表后，立即删除 worker:{id}:profile 缓存，下次读取重建
- workers:online Set：维修员登录/下线触发SADD/SREM，保障在岗集合实时准确

### 5.5 MongoDB 文档数据库设计

职责定位：存储Schema不固定的半结构化文档（AI解析JSON、维修记录、图片元数据、审计日志），天然适配AI工作流输出，避免MySQL频繁ALTER TABLE。

| Collection | 文档结构（字段定义） | 说明 |
|------------|-------------------|------|
| ticket_attachments（工单附件文档） | ticket_id, type(report_photo/completion_photo), uploader_id, image_url, gps:{lng,lat}, timestamp, watermark_hash, ai_result:{fault_type,confidence,verified} | 存储报修照片、完工照片元数据及AI视觉核验结果。image_url指向OSS，watermark_hash防篡改 |
| ai_analysis_logs（AI解析日志） | ticket_id, workflow(nlp_parse/dispatch_score/ai_verify), input:Object, output:Object, confidence, model_version, created_at | 存储Dify三大工作流的输入/输出JSON，AI返回的schema不固定，MongoDB天然适配 |
| repair_records（维修详情记录） | ticket_id, worker_id, materials:[{name,qty,unit,unit_cost}], labor_hours, work_notes, before_photos:[url], after_photos:[url], gps_checkin:{lng,lat}, gps_checkin_at, completed_at | 材料耗材数组结构灵活（不同设施类型耗材种类差异大），工时、备注、签到坐标一体存储 |
| audit_logs（操作审计日志） | operator_id, role, action, target:{type,id}, old_value:Object, new_value:Object, ip, ua, created_at | 全系统后台操作记录，append-only权限，禁止DELETE/UPDATE操作 |
| notifications（消息通知） | recipient_id, recipient_role, type, title, content:Object, related_id, is_read, created_at | 系统消息通知文档，content字段因通知类型而异（Schema不固定） |

MongoDB 使用规范：
- 所有Collection按业务模块划分，禁止跨业务模块共用Collection
- ticket_id 在各Collection中均建立索引，支持按工单ID快速聚合所有相关文档
- audit_logs Collection设置append-only权限，禁止DELETE/UPDATE操作，满足政务审计不可篡改要求
- 图片文件本体存储OSS，MongoDB仅存元数据（URL、尺寸、GPS、水印Hash），单文档不超过16MB限制
- ai_analysis_logs的input/output字段为任意JSON Object，充分利用MongoDB Schema灵活特性

### 5.6 Elasticsearch 检索与聚合分析设计

职责定位：提供工单全文检索（IK中文分词）、故障分布聚合统计、绩效排行分析、GeoPoint空间查询，是数据驾驶舱的核心算力支撑。

| Index名称 | 核心Mapping字段 & 业务用途 |
|-----------|------------------------|
| tickets_index | ticket_id(keyword), status(keyword), facility_type(keyword), district(keyword), description(text/ik_max_word), nlp_confidence(float), location(geo_point), created_at(date), assigned_worker_id(keyword), closed_at(date) → 支持工单关键词全文检索、地理围栏聚合、时间段统计、故障类型TOP分析 |
| facilities_index | facility_code(keyword), type(keyword), address(text), location(geo_point), district(keyword), install_date(date), fault_count(integer) → 设施档案全文检索、故障高发设施聚合、片区设施分布GIS渲染 |
| workers_perf_index | worker_id(keyword), name(keyword), district(keyword), total_orders(integer), avg_response_minutes(float), avg_star(float), bad_review_count(integer), settlement_total(float), date(date) → 维修员绩效排行、响应速度分析、好评率聚合、日/周/月绩效看板 |
| audit_log_index | operator_id(keyword), role(keyword), action(keyword), target_type(keyword), target_id(keyword), created_at(date), ip(keyword) → 操作审计全文检索、敏感操作追踪、导出审计报告（预留，暂未通过Logstash同步） |

ES 同步策略（RabbitMQ 可靠异步投递 + DLQ 死信队列）：
- 工单数据：所有状态变更点（创建/派单/接单/签到/完工/市民确认/超时关闭/强制指派）通过 `publish_es_sync(ticket_id)` 发布到 RabbitMQ `es_sync` 队列
- ES Sync 消费者：从 MySQL 全量加载完整 Ticket 文档 → `es.index()` upsert → 成功 ack → 失败发布到 `es_sync.delay`（per-message TTL 指数退避 2s→4s→8s→16s→32s→DLQ）
- 超过最大重试次数（ES_SYNC_MAX_RETRIES=5）→ 路由到 `es_sync.dlq` 死信队列，管理员手动处理
- 调用方 fire-and-forget：只负责发布消息，RabbitMQ 不可用时工单安全在 MySQL，定期全量同步脚本兜底
- 绩效数据：评价提交时通过 ES Script 增量更新 workers_perf_index（upsert 语义）
- IK中文分词：所有text类型字段统一使用 ik_max_word 索引分词，ik_smart 查询分词

---

## 六、分层技术架构设计

### 6.1 五层整体架构说明

系统采用五层架构：前端交互层 → API网关服务层 → AI智能引擎层 → 消息数据中间层 → 底层持久化层。

```
【前端交互层】市民小程序(Vue3) · 维修员H5(Vue3) · 管理后台(Vue3+ElementPlus)
      ↕ HTTP ↕
【API网关服务层】FastAPI 异步网关 · JWT鉴权 · RBAC权限 · 接口限流 · OpenAPI文档
      ↕ 业务调用 ↕
【AI智能引擎层】Dify 编排平台 · 工作流1:报修NLP+OCR · 工作流2:派单评分 · 工作流3:AI验收
      ↕ 读写中间层 ↕
【消息数据中间层】Redis(缓存/锁/Geo/计数) · RabbitMQ(派单队列/超时延迟/差评复核/ES同步+DLQ) · MongoDB(文档存储/审计)
      ↕ 持久化联动 ↕
【底层持久化层】MySQL(结构化主库) · Elasticsearch(检索/聚合分析)
```

### 6.2 接口规范设计（含四库存储联动标注）

路由前缀：市民 /api/v1/citizen · 维修员 /api/v1/worker · 管理员 /api/v1/admin · 通用 /api/v1/auth 和 /api/v1/utils

统一返回体：`{"code":200, "msg":"提示文案", "data":业务数据}`
错误码：200成功 · 401鉴权失效 · 403权限不足 · 400参数错误 · 500服务异常

#### 6.2.1 统一认证

| Method | 路由 | 接口说明 | 数据存储联动 |
|--------|------|---------|------------|
| POST | /api/v1/auth/login | 用户名+密码统一登录（三端共用） | MySQL users 验证；worker角色自动SADD workers:online + GEOADD workers:geo；三级定位降级（GPS→IP→默认） |
| POST | /api/v1/auth/register | 用户名+密码注册（默认citizen角色） | MySQL users 写入；bcrypt密码哈希 |
| POST | /api/v1/auth/sms/send | 发送短信验证码 | 腾讯云短信SDK发送6位验证码；Redis sms:{phone} 缓存，5分钟过期，60s防重发 |
| POST | /api/v1/auth/sms/login | 短信验证码登录（市民端） | Redis验证码校验 → MySQL users查找/创建 → 返回JWT Token |

#### 6.2.2 市民端 /api/v1/citizen

| Method | 路由 | 接口说明 | 数据存储联动 |
|--------|------|---------|------------|
| POST | /api/v1/citizen/tickets | 市民提交报修工单 | 写MySQL tickets表 → Redis缓存 → MongoDB存AI解析结果+图片元数据 → RabbitMQ dispatch入队 + es_sync入队 |
| GET | /api/v1/citizen/tickets/{id} | 查询工单实时进度 | Redis热查ticket:{tid}:info缓存，Miss则降级MySQL查询；MongoDB repair_records构建时间轴 |
| GET | /api/v1/citizen/tickets | 查询当前用户历史工单列表 | MySQL tickets 按user_id分页查询 |
| POST | /api/v1/citizen/evaluations | 市民提交服务评价 | 写MySQL evaluations；差评(star≤2)触发RabbitMQ review_queue；ES workers_perf_index Script更新绩效；MongoDB notifications通知维修员 |

#### 6.2.3 维修员端 /api/v1/worker

| Method | 路由 | 接口说明 | 数据存储联动 |
|--------|------|---------|------------|
| GET | /api/v1/worker/tickets/queue | 工单接单大厅（按距离排序） | MySQL 查询 pending/dispatching/repairing 工单；Redis workers:geo GEOPOS 计算距离；按距离升序排列 |
| GET | /api/v1/worker/tickets/{id} | 工单详情（含全流程时间轴） | MySQL tickets 完整字段查询；构建时间轴（created→accepted→started→completed→closed） |
| GET | /api/v1/worker/tickets | 我的工单列表（分页） | MySQL tickets 按 assigned_worker_id 查询 |
| PUT | /api/v1/worker/tickets/{id}/accept | 维修员接单确认 | Redis SETNX 获取分布式锁 → MySQL 更新 assigned_worker_id + status→repairing → Redis 状态缓存 + 计数+1 → 释放锁；ES同步 via RabbitMQ |
| PUT | /api/v1/worker/tickets/{id}/checkin | 到场签到 | MongoDB repair_records upsert GPS签到坐标 → MySQL 更新 started_at + status→repairing → Redis 状态缓存；ES同步 via RabbitMQ |
| PUT | /api/v1/worker/location | 实时位置上报 | Redis workers:geo GEOADD 更新坐标 |
| PUT | /api/v1/worker/tickets/{id}/complete | 完工提交 | MongoDB repair_records 存耗材+工时+完工照片 → MongoDB ticket_attachments 存完工照片 → Dify AI验收 → 通过：MySQL status→verifying；未通过：status保持repairing → Redis缓存同步；ES同步 via RabbitMQ |
| GET | /api/v1/worker/performance | 查询个人绩效 | Redis worker:{id}:daily_order 获取今日接单数 |

#### 6.2.4 管理后台 /api/v1/admin

| Method | 路由 | 接口说明 | 数据存储联动 |
|--------|------|---------|------------|
| GET | /api/v1/admin/dashboard/realtime | 驾驶舱实时指标 | MySQL 实时查询今日新增/待派/处理中/验收中/完结工单；Redis workers:online SCARD 在岗人数 |
| GET | /api/v1/admin/dashboard/analytics | 驾驶舱聚合统计 | MySQL 聚合查询（总工单量/平均响应时长/好评率/TOP10设施/片区分布/近6月趋势） |
| GET | /api/v1/admin/tickets/search | 工单全文检索（含日期范围） | ES tickets_index 全文检索（IK中文分词）优先；MySQL降级兜底；支持关键词/状态/设施类型/行政区/创建时间范围筛选 |
| POST | /api/v1/admin/tickets/{id}/dispatch | 人工强制指派工单 | Redis强制释放分布式锁 → MySQL更新工单 → MongoDB写审计日志 → Redis缓存同步；ES同步 via RabbitMQ |
| GET | /api/v1/admin/workers | 维修员列表（含在线状态+位置） | MySQL workers 查询；Redis workers:online + workers:geo + worker:{id}:daily_order 追加实时数据 |
| PUT | /api/v1/admin/workers/{id} | 更新维修员档案 | MySQL workers 更新 → Redis worker:{id}:profile 缓存失效 |
| GET | /api/v1/admin/facilities | 设施档案列表 | MySQL facilities 分页查询，支持按行政区/设施类型筛选 |
| GET | /api/v1/admin/settlements | 结算单列表 | MySQL settlements 分页查询，支持按审核状态筛选 |
| PUT | /api/v1/admin/settlements/{id}/audit | 结算审核（通过/驳回） | MySQL settlements 更新 audit_status + auditor_id |
| GET | /api/v1/admin/audit-logs | 审计日志查询 | MongoDB audit_logs 按操作人/操作类型筛选，时间倒序 |
| GET | /api/v1/admin/config | 读取结算规则配置 | MySQL audit_rules 查询全部规则 |
| PUT | /api/v1/admin/config | 批量更新结算规则 | MySQL audit_rules 批量更新 |
| POST | /api/v1/admin/config | 新增设施品类结算规则 | MySQL audit_rules 插入新规则 |

#### 6.2.5 工具类 /api/v1/utils

| Method | 路由 | 接口说明 | 数据存储联动 |
|--------|------|---------|------------|
| GET | /api/v1/utils/reverse-geocode | 逆地理编码（GPS→地址） | 高德API逆地理编码 |
| POST | /api/v1/utils/upload-image | 图片上传到OSS | oss2 SDK 直传阿里云OSS（北京地域），返回公网URL |

---

## 七、全模块功能详细设计

### 7.1 市民端小程序

| 核心页面 | 页面功能详情 | 数据存储联动 |
|----------|------------|------------|
| 首页 | 居中快速报修按钮、近期工单快捷入口、个人积分展示、系统公告弹窗、短信验证码登录 | MySQL users读取用户信息；Redis counter积分读取；MySQL tickets查询最近工单 |
| AI报修提交页 | 自动定位、AI预填设施品类、文本实时纠错、图片压缩上传、重复工单智能提示 | 写MySQL tickets主表；AI解析写MongoDB ai_analysis_logs；图片元数据写MongoDB ticket_attachments；ES查重检索 |
| 工单进度页 | 全流程时间轴、脱敏维修员点位、工单流转节点备注、消息回溯 | Redis ticket:{tid}:info热缓存；维修员坐标Redis Geo脱敏处理 |
| 服务评价页 | 星级评分、快捷评价标签、文字补充、差评申诉入口 | 写MySQL evaluations；差评触发RabbitMQ延迟队列；ES workers_perf_index绩效联动更新 |
| 个人中心页 | 1年内报修历史、积分明细、系统消息、隐私设置、草稿管理 | MySQL tickets历史查询；Redis积分计数；MongoDB notifications未读消息；本地离线草稿存储 |

### 7.2 维修员移动端H5

| 核心页面 | 页面功能详情 | 数据存储联动 |
|----------|------------|------------|
| 实时接单大厅 | 工单按距离排序、工单紧急度标签、一键接单、忙碌免打扰 | MySQL tickets查询；Redis workers:online维护在线状态；Redis workers:geo计算距离 |
| 工单详情页 | 故障原图、设施档案、AI维修方案、一键导航、周边联动工单查看 | MySQL tickets+facilities关联查询；MongoDB ticket_attachments原图；ES检索周边工单；Dify推荐写MongoDB ai_analysis_logs |
| 完工闭环页 | 水印拍照、耗材录入、工时填报、完工提交、返工原因填报 | MongoDB repair_records存耗材数组；MongoDB ticket_attachments存完工图片元数据；Dify AI验收结果写MongoDB；MySQL工单状态更新 |
| 绩效中心 | 日周月工单统计、好评排行、结算预估、违规扣分台账 | ES workers_perf_index聚合绩效；Redis worker:{id}:daily_order实时计数；MySQL settlements结算预估 |

### 7.3 市政管理PC后台

| 功能模块 | 模块核心功能 | 数据存储联动 |
|----------|------------|------------|
| GIS工单调度台 | 高德地图全域设施点位、在岗维修员实时点位、工单筛选、强制指派、工单冻结 | 高德JS API地图渲染；Redis workers:geo维修员实时点位；ES geo_point设施分布；MySQL工单筛选；Redis分布式锁管控；MongoDB audit_logs记录人工操作 |
| 人员权限管理 | 维修员增删改查、技能标签配置、排班管理、在岗状态管控、角色权限分配 | MySQL workers + users RBAC权限；Redis worker:{id}:profile缓存；变更后Redis缓存失效重建 |
| 运维结算管理 | 自动生成结算单、费用审核、费用导出、违规扣款溯源、外包班组对账 | MySQL settlements + audit_rules；MongoDB repair_records耗材成本核算；MongoDB audit_logs溯源；不对接财务系统 |
| 可视化数据看板 | 六大运维指标可视化、自定义周期统计、报表导出、数据大屏全屏展示 | MySQL实时查询（今日数字）；ES Aggregation聚合（历史趋势）；MySQL结算报表；MongoDB审计日志 |
| 系统热配置 | 派单权重、超时时长、计价标准、消息模板、积分规则可视化修改 | MySQL audit_rules持久化配置；Redis config:*缓存热读，修改即时生效无需重启服务 |

---

## 八、非功能需求与系统质量指标

| 指标分类 | 量化指标要求 | 技术保障手段 |
|----------|------------|------------|
| 并发性能 | 核心接口P99响应时间≤500ms，派单接口≤200ms | Redis热点缓存、FastAPI异步、RabbitMQ异步解耦 |
| 数据一致性 | 工单状态变更保障MySQL事务+Redis缓存最终一致 | MySQL事务+Redis延迟双删防脏数据 |
| 存储可靠性 | MySQL主库binlog备份，MongoDB副本集，ES单副本 | 毕设体量适配，生产建议3副本 |
| 查询性能 | 工单全文检索≤200ms，ES聚合统计≤1s | ES IK中文分词，合理Mapping，避免深分页 |
| 数据安全 | 手机号脱敏存储，图片URL签名访问，审计日志不可删 | MongoDB audit_logs append-only，OSS STS临时授权 |
| 系统可用性 | 核心功能SLA≥99%，Redis宕机MySQL降级兜底 | 毕设演示稳定性优先，Redis单节点可接受 |
| 扩展性 | MySQL分库分表预留，MongoDB水平扩展，ES横向扩节点 | 毕设单机，架构预留扩展接口 |

---

## 九、项目开发里程碑规划

| 阶段 | 时间规划 | 核心交付物 | 四库存储验收点 |
|------|---------|----------|-------------|
| M1 | 第1-2周 | 环境搭建 + 数据库初始化 | MySQL建库建表、Redis部署、MongoDB初始化Collection、ES创建Index+IK分词、FastAPI骨架、RabbitMQ队列声明 |
| M2 | 第3-4周 | 核心业务开发（市民报修+工单） | 短信登录、报修提交、MySQL写工单主表、MongoDB存AI解析结果、Redis缓存工单状态、RabbitMQ入队 |
| M3 | 第5-6周 | AI派单 + 维修闭环 | Dify多维评分工作流、Redis Geo派单、分布式锁、MongoDB存维修记录、Dify AI验收 |
| M4 | 第7-8周 | 管理后台 + 数据驾驶舱 | GIS调度台、ES全文检索、ES聚合统计、Redis驾驶舱实时指标、MongoDB审计日志查询 |
| M5 | 第9-10周 | 联调测试 + 演示数据填充 | 端到端联调、模拟1000条设施+100条工单、压力测试、答辩PPT准备 |

---

## 十、项目边界与开发范围说明

### 10.1 明确纳入范围（Need to Have）
- MySQL建表建库，完整业务CRUD接口开发
- Redis六大核心场景：状态缓存、Geo派单、分布式锁、计数器、Set在岗维护、热配置
- MongoDB五个Collection：图片元数据、AI解析日志、维修记录、审计日志、通知消息
- Elasticsearch四个Index：工单检索、设施档案、绩效统计、审计日志全文检索
- Dify三大工作流：报修NLP解析、多维派单评分、AI验收比对（未配置时降级为本地模拟/简单算法）
- RabbitMQ五个队列：派单队列(dispatch)、超时延迟队列(dispatch_timeout)、差评复核队列(review_queue)、ES同步队列(es_sync)、ES延迟重试队列(es_sync.delay) + ES死信队列(es_sync.dlq)
- ES Sync 可靠性架构：RabbitMQ 异步投递 + 消费者全量加载 MySQL + 指数退避重试（2s→4s→8s→16s→32s）+ DLQ 死信队列
- 三端前端：市民小程序、维修员H5、管理后台
- 高德地图集成：逆地理编码、驾车距离修正、IP定位、GIS地图渲染
- 阿里云OSS图片上传（北京地域）：服务端oss2 SDK直传，按tickets/YYYY/MM/DD/{uuid}.ext组织

### 10.2 明确排除范围（Nice to Have，超出毕设体量）
- IoT设备对接与实时传感器故障预警（无硬件资源）
- AI预测性运维与故障趋势预测（无多年历史训练数据）
- 对接政务财务对公系统与第三方支付接口（无正式政务账号）
- 城市实时交通路况接口对接（仅使用模拟路况数据）
- MySQL主从复制与Redis集群（单机毕设演示可接受）
- 原生安卓/iOS APP开发（仅覆盖H5与小程序）
- 实时双向通信（当前使用HTTP轮询/主动查询模式，仅做单向服务端→客户端数据查询）
- Logstash管道同步审计日志到ES（当前仅RabbitMQ同步工单数据）
- rabbitmq_delayed_message_exchange 插件（dispatch_timeout使用x-delay header，当前exchange为DIRECT类型，此为已知限制）

---

## 十一、术语表与面试答辩话术参考

| 术语 | 解释说明（含面试答辩口径） |
|------|------------------------|
| 四库分层存储 | MySQL负责结构化事务数据，Redis负责热点缓存和实时计算，MongoDB负责非结构化文档，ES负责全文检索和聚合分析。各司其职，避免单库过载，同时充分利用各数据库核心优势。 |
| Redis分布式锁 | SETNX+EXPIRE原子操作锁定工单派单权，300s自动过期防死锁，保障并发场景下同一工单不会被同时派给两名维修员。 |
| MongoDB文档模型 | AI解析结果JSON Schema不固定（不同故障类型字段不同），MongoDB无需预定义Schema，天然适配AI工作流输出；维修耗材数组长度不固定，嵌入文档存储避免MySQL多表JOIN。 |
| ES聚合统计 | 利用ES Aggregation（terms/avg/date_histogram/geo_distance）实现驾驶舱多维统计，替代MySQL复杂GROUP BY，毫秒级返回故障TOP分析、时间序列趋势、地理分布热力。 |
| Redis-MySQL一致性 | 采用Cache-Aside模式：先写MySQL事务成功，再删Redis缓存，延迟500ms二次删除防并发脏读。不用Canal/binlog是因为毕设体量无需引入更多中间件复杂度。 |
| ES同步可靠投递 | 所有工单状态变更点通过RabbitMQ发布es_sync消息（fire-and-forget），ES Sync消费者从MySQL全量加载完整文档后es.index() upsert；失败进入指数退避重试（2s→4s→8s→16s→32s），超过5次进入DLQ死信队列待人工处理。 |
| MongoDB-ES同步 | 工单数据通过RabbitMQ ES Sync消费者实时同步；绩效数据通过评价提交时ES Script增量更新。审计日志暂未通过Logstash同步至ES audit_log_index（预留接口）。 |
| IK中文分词 | ES标准分词对中文效果极差（按字切分），IK分词器（ik_max_word细粒度/ik_smart粗粒度）针对中文语义分词，使「道路灯杆故障」能正确匹配「灯杆」「故障」等关键词。 |
| 高德驾车距离修正 | 派单时用高德驾车路径规划API获取实际路面距离，替换Redis Geo直线距离（缓存5分钟），失败时降级保持Geo直线距离，确保派单距离精度。 |
| 三级定位降级 | 维修员登录定位：前端GPS（精度~10m）→ 高德IP定位（精度~500m-5km）→ 默认长沙中心兜底（112.9388, 28.2282）。 |
| 短信验证码登录 | 市民端通过手机号+短信验证码登录，腾讯云短信SDK发送6位数字验证码，Redis缓存验证码（5分钟过期，60s防重发），验证通过后签发JWT Token。替代微信授权登录，降低小程序开发门槛，无需微信开放平台资质。 |
| HTTP轮询进度更新 | 市民端工单进度页通过HTTP定时轮询（间隔5-10s）获取最新工单状态，替代WebSocket双向通信。服务端仅提供RESTful查询接口，客户端主动拉取，架构更简单，无需维护长连接。 |

---

城市公共设施智能报修与派单系统 · PRD v3.3
