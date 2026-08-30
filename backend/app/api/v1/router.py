# ============================================================
# 城市公共设施智能报修与派单系统 - API 路由汇总
# 作用：汇聚 citizen/worker/admin 三个子路由，统一挂载到 app；
#       路由前缀：/api/v1/citizen, /api/v1/worker, /api/v1/admin
# ============================================================

from fastapi import APIRouter

from app.api.v1.auth import router as unified_auth_router
from app.api.v1.citizen.tickets import router as citizen_tickets_router
from app.api.v1.citizen.evaluations import router as citizen_eval_router

from app.api.v1.worker.auth import router as worker_auth_router
from app.api.v1.worker.tickets import router as worker_tickets_router
from app.api.v1.worker.notifications import router as worker_notifications_router
from app.api.v1.worker.performance import router as worker_perf_router

from app.api.v1.admin.auth import router as admin_auth_router
from app.api.v1.admin.dashboard import router as admin_dashboard_router
from app.api.v1.admin.tickets import router as admin_tickets_router
from app.api.v1.admin.workers import router as admin_workers_router
from app.api.v1.admin.facilities import router as admin_facilities_router
from app.api.v1.admin.settlements import router as admin_settlements_router
from app.api.v1.admin.audit_logs import router as admin_audit_router
from app.api.v1.admin.config import router as admin_config_router
from app.api.v1.utils import router as utils_router
from app.api.v1.upload import router as upload_router

api_router = APIRouter()

# 统一登录 /api/v1/auth（用户名+密码，三端共用）
api_router.include_router(unified_auth_router, prefix="/auth", tags=["统一-认证"])

# 市民端 /api/v1/citizen
api_router.include_router(citizen_tickets_router, prefix="/citizen", tags=["市民-工单"])
api_router.include_router(citizen_eval_router, prefix="/citizen", tags=["市民-评价"])

# 维修员端 /api/v1/worker
api_router.include_router(worker_auth_router, prefix="/worker", tags=["维修员-认证"])
api_router.include_router(worker_tickets_router, prefix="/worker", tags=["维修员-工单"])
api_router.include_router(worker_notifications_router, prefix="/worker/notifications", tags=["维修员-通知"])
api_router.include_router(worker_perf_router, prefix="/worker", tags=["维修员-绩效"])

# 管理后台 /api/v1/admin
api_router.include_router(admin_auth_router, prefix="/admin", tags=["管理-认证"])
api_router.include_router(admin_dashboard_router, prefix="/admin", tags=["管理-驾驶舱"])
api_router.include_router(admin_tickets_router, prefix="/admin", tags=["管理-工单"])
api_router.include_router(admin_workers_router, prefix="/admin", tags=["管理-人员"])
api_router.include_router(admin_facilities_router, prefix="/admin", tags=["管理-设施"])
api_router.include_router(admin_settlements_router, prefix="/admin", tags=["管理-结算"])
api_router.include_router(admin_audit_router, prefix="/admin", tags=["管理-审计"])
api_router.include_router(admin_config_router, prefix="/admin", tags=["管理-配置"])

# 工具类（无需角色鉴权）
api_router.include_router(utils_router, prefix="/utils", tags=["工具"])
api_router.include_router(upload_router, prefix="/utils", tags=["工具-上传"])
