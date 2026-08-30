# ============================================================
# 城市公共设施智能报修与派单系统 - 用户密码字段迁移脚本
# 作用：为已有 users 表添加 username + password_hash 列，
#       并更新现有用户写入登录凭据
# 运行方式：cd backend && python update_user_credentials.py
# ============================================================

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text, select
from app.config.mysql import engine, async_session_factory
from app.models.mysql.user import User
from app.core.security import hash_password

# 已有用户的登录凭据映射
USER_CREDENTIALS = {
    "A0001": {"username": "admin",    "password": "admin123"},
    "U0001": {"username": "zhangsan", "password": "123456"},
    "U0002": {"username": "lisi",     "password": "123456"},
    "W0001": {"username": "worker1",  "password": "123456"},
    "W0002": {"username": "worker2",  "password": "123456"},
}


async def main():
    print("=" * 60)
    print("User credential migration")
    print("=" * 60)

    # 1. ALTER TABLE - add username and password_hash columns
    async with engine.begin() as conn:
        for col, col_def in [
            ("username", "VARCHAR(64) NULL UNIQUE COMMENT 'login username'"),
            ("password_hash", "VARCHAR(256) NULL COMMENT 'bcrypt password hash'"),
        ]:
            try:
                await conn.execute(
                    text(f"ALTER TABLE users ADD COLUMN {col} {col_def}")
                )
                print(f"[OK] Added column: {col}")
            except Exception as e:
                if "Duplicate column" in str(e) or "already exists" in str(e).lower():
                    print(f"[SKIP] Column already exists: {col}")
                else:
                    print(f"[FAIL] Column add failed {col}: {e}")
                    return

    # 2. Update existing users with username + password_hash
    updated = 0
    async with async_session_factory() as session:
        for user_id, creds in USER_CREDENTIALS.items():
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                print(f"[SKIP] User not found: {user_id}")
                continue

            if user.username and user.password_hash:
                print(f"[SKIP] {user_id} already has credentials")
                continue

            user.username = creds["username"]
            user.password_hash = hash_password(creds["password"])
            print(f"[OK] {user_id} ({creds['username']}) credentials set")
            updated += 1

        await session.commit()

    print()
    print(f"[DONE] {updated} users updated")
    print()
    print("Test login:")
    print('  curl -X POST http://127.0.0.1:8000/api/v1/auth/login ^')
    print('    -H "Content-Type: application/json" ^')
    print('    -d "{\\"username\\":\\"admin\\",\\"password\\":\\"admin123\\"}"')
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
