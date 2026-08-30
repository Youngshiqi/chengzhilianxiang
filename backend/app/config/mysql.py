# ============================================================
# 城市公共设施智能报修与派单系统 - MySQL 连接管理
# 作用：管理 SQLAlchemy 异步引擎和会话工厂；
#       存储 users/tickets/facilities/workers/settlements/evaluations/audit_rules 七张核心业务表；
#       提供 get_db 依赖注入函数，保障事务一致性和外键约束
# ============================================================

from sqlalchemy import MetaData, inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# 异步引擎（aiomysql 驱动）
# charset=utf8mb4 设置客户端连接字符集；
# init_command 设置会话时区为北京时间（+08:00）；
# 服务端数据库/表/列的字符集由 DDL 决定，见 init_mysql() 中的校验逻辑
engine = create_async_engine(
    f"mysql+aiomysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
    f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    f"?charset=utf8mb4&init_command=SET+time_zone%3D%27%2B08%3A00%27",
    pool_size=settings.MYSQL_POOL_SIZE,
    echo=settings.DEBUG,
)

# 异步会话工厂
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类，所有 MySQL 模型继承此类"""
    pass


async def init_mysql():
    """应用启动时：校验数据库字符集 + 创建所有表 + 自动补齐缺失列"""
    # 确保所有 ORM 模型已注册到 Base.metadata
    import app.models.mysql.user           # noqa: F401
    import app.models.mysql.ticket         # noqa: F401
    import app.models.mysql.facility       # noqa: F401
    import app.models.mysql.worker         # noqa: F401
    import app.models.mysql.settlement     # noqa: F401
    import app.models.mysql.evaluation     # noqa: F401
    import app.models.mysql.audit_rule     # noqa: F401

    async with engine.begin() as conn:
        # 确保数据库级字符集为 utf8mb4
        await conn.execute(text(
            f"ALTER DATABASE `{settings.MYSQL_DATABASE}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        ))
        # 建表（新表继承数据库默认字符集 utf8mb4）
        await conn.run_sync(Base.metadata.create_all)

    # 确保已有表的字符集正确（幂等：已是 utf8mb4 的表不受影响）
    await _ensure_table_charsets()

    # 自动补齐缺失列（已有表新增字段时）
    await _ensure_columns()


async def _ensure_table_charsets():
    """将核心业务表统一转为 utf8mb4（幂等操作，不影响已有正确数据）"""
    async with engine.begin() as conn:
        tables = await conn.execute(text(
            "SELECT TABLE_NAME FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = :db AND TABLE_COLLATION != 'utf8mb4_unicode_ci'",
        ), {"db": settings.MYSQL_DATABASE})
        bad_tables = [row[0] for row in tables.fetchall()]

        for tbl in bad_tables:
            logger.warning(f"表 {tbl} 字符集不是 utf8mb4，正在转换...")
            await conn.execute(text(
                f"ALTER TABLE `{tbl}` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            ))
            logger.info(f"表 {tbl} 已转为 utf8mb4_unicode_ci")


def _build_default_clause(col) -> str:
    """根据 ORM 列默认值生成 SQL DEFAULT 子句"""
    if col.default is None:
        return ""
    arg = col.default.arg
    if arg is None:
        return ""
    if callable(arg):
        return ""  # Python 可调用默认值（如 datetime.utcnow）不能在 ALTER TABLE 中表达
    if isinstance(arg, str):
        if arg == "":
            return " DEFAULT ''"
        return f" DEFAULT '{arg}'"
    return f" DEFAULT {arg}"


async def _ensure_columns():
    """自动补齐 ORM 模型定义中存在但数据库表中缺失的列（轻量级迁移）"""
    from app.models.mysql.ticket import Ticket

    async with engine.begin() as conn:
        def _sync_columns(connection):
            inspector = inspect(connection)
            for model, table_name in [(Ticket, "tickets")]:
                existing = {c["name"] for c in inspector.get_columns(table_name)}
                for col in model.__table__.columns:
                    if col.name not in existing:
                        col_type = col.type.compile(connection.dialect)
                        nullable = "NULL" if col.nullable else "NOT NULL"
                        default_clause = _build_default_clause(col)
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type} {nullable}{default_clause}"
                        logger.info(f"补齐缺失列: {sql}")
                        connection.execute(text(sql))

                # 补齐索引
                existing_indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}
                for idx in model.__table__.indexes:
                    if idx.name and idx.name not in existing_indexes:
                        cols = ", ".join(c.name for c in idx.columns)
                        sql = f"CREATE INDEX {idx.name} ON {table_name}({cols})"
                        logger.info(f"补齐缺失索引: {sql}")
                        connection.execute(text(sql))

        await conn.run_sync(_sync_columns)


async def close_mysql():
    """应用关闭时：释放连接池"""
    await engine.dispose()


def get_async_session_factory():
    """返回异步会话工厂（供 RabbitMQ 消费者等非请求上下文使用）"""
    return async_session_factory


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取异步数据库会话，请求结束后自动关闭"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
