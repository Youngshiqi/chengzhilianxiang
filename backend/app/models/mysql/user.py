# ============================================================
# 城市公共设施智能报修与派单系统 - users 用户账号表 ORM 模型
# 作用：存储市民/维修员/管理员三方账号基础信息；
#        role 字段控制 RBAC 权限（citizen/worker/admin）；
#        phone 字段脱敏存储（仅存后四位掩码）
# 对应 MySQL 表：users
# ============================================================

import datetime
from sqlalchemy import String, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.mysql.base import Base
from app.utils.timezone import now_beijing


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(32), primary_key=True, comment="用户唯一ID")
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=True, comment="登录用户名")
    password_hash: Mapped[str] = mapped_column(String(256), nullable=True, comment="bcrypt密码哈希")
    openid: Mapped[str] = mapped_column(String(64), unique=True, nullable=True, comment="微信OpenID")
    phone: Mapped[str] = mapped_column(String(16), comment="手机号（脱敏存储）")
    phone_normalized: Mapped[str | None] = mapped_column(
        String(16), unique=True, nullable=True,
        comment="阿里云号码认证返回的真实手机号，用于一键登录查找"
    )
    role: Mapped[str] = mapped_column(
        SAEnum("citizen", "worker", "admin", name="user_role"),
        default="citizen",
        comment="角色: citizen=市民 worker=维修员 admin=管理员",
    )
    nickname: Mapped[str] = mapped_column(String(64), comment="用户昵称")
    avatar_url: Mapped[str] = mapped_column(String(512), nullable=True, comment="头像URL")
    district: Mapped[str] = mapped_column(String(64), nullable=True, comment="所属行政区")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=now_beijing, comment="注册时间"
    )
    is_active: Mapped[bool] = mapped_column(default=True, comment="账号启用状态")
