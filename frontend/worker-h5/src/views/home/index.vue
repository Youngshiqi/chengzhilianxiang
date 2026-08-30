<!--
  城市设施报修 · 维修工端 — 工作台
  重工仪表：仪表盘绩效卡片 + 安全橙快捷入口
-->
<template>
  <div class="home-page">
    <!-- 顶栏 -->
    <header class="header">
      <div class="header-left">
        <div class="header-logo">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="9" />
            <circle cx="12" cy="12" r="3" />
            <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
          </svg>
        </div>
        <div class="header-name mono">{{ workerName }}</div>
      </div>
      <div class="header-right">
        <button class="btn-notification" @click="goToNotifications">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          <span v-if="unreadCount > 0" class="notification-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
        </button>
        <button class="btn-logout" @click="openChangePassword" title="修改密码">
          <span class="logout-icon">🔑</span>
        </button>
        <button class="btn-logout" @click="handleLogout">
          <span class="logout-icon">⏻</span>
        </button>
      </div>
    </header>

    <!-- 绩效仪表卡片 -->
    <section class="stats-grid">
      <div class="stat-card sc-orange">
        <div class="sc-bg-bar"></div>
        <div class="sc-value mono">{{ perf.today_orders }}</div>
        <div class="sc-label">今日接单</div>
        <div class="sc-gauge">
          <span class="gauge-ticks"></span>
        </div>
      </div>
      <div class="stat-card sc-blue">
        <div class="sc-bg-bar"></div>
        <div class="sc-value mono">{{ perf.month_orders }}</div>
        <div class="sc-label">本月工单</div>
        <div class="sc-gauge">
          <span class="gauge-ticks"></span>
        </div>
      </div>
      <!-- 【待开发】好评率功能
      <div class="stat-card sc-green">
        <div class="sc-bg-bar"></div>
        <div class="sc-value mono">{{ perf.avg_star }}<small> ★</small></div>
        <div class="sc-label">好评率</div>
        <div class="sc-gauge">
          <span class="gauge-ticks"></span>
        </div>
      </div>
      -->
      <!-- 【待开发】总结算功能
      <div class="stat-card sc-purple">
        <div class="sc-bg-bar"></div>
        <div class="sc-value mono">¥{{ perf.settlement_estimate }}</div>
        <div class="sc-label">总结算</div>
        <div class="sc-gauge">
          <span class="gauge-ticks"></span>
        </div>
      </div>
      -->
    </section>

    <!-- 快捷入口 -->
    <section class="quick-actions">
      <router-link to="/queue" class="action-card action-primary">
        <span class="action-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
          </svg>
        </span>
        <div class="action-info">
          <span class="action-title">接单大厅</span>
          <span class="action-desc">查看待接工单，按距离排序</span>
        </div>
        <span class="action-arrow">→</span>
      </router-link>
      <router-link to="/my-tickets" class="action-card">
        <span class="action-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
        </span>
        <div class="action-info">
          <span class="action-title">我的工单</span>
          <span class="action-desc">查看和处理已接工单</span>
        </div>
        <span class="action-arrow">→</span>
      </router-link>
    </section>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">
      <span class="load-ring"></span>
      <span>加载中...</span>
    </div>

    <!-- 修改密码弹窗 -->
    <div v-if="showPasswordDialog" class="modal-overlay" @click.self="closePasswordDialog">
      <div class="modal-card">
        <div class="modal-header">
          <span class="modal-title">修改密码</span>
          <button class="modal-close" @click="closePasswordDialog">×</button>
        </div>
        <div class="modal-body">
          <div class="form-item">
            <label class="form-label">原密码</label>
            <div class="input-wrapper">
              <input :type="showOldPassword ? 'text' : 'password'" class="form-input" v-model="passwordForm.old" placeholder="请输入原密码" />
              <button type="button" class="toggle-eye" @click="showOldPassword = !showOldPassword">
                <svg v-if="!showOldPassword" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
              </button>
            </div>
          </div>
          <div class="form-item">
            <label class="form-label">新密码</label>
            <div class="input-wrapper">
              <input :type="showNewPassword ? 'text' : 'password'" class="form-input" v-model="passwordForm.new" placeholder="请输入新密码（至少6位）" />
              <button type="button" class="toggle-eye" @click="showNewPassword = !showNewPassword">
                <svg v-if="!showNewPassword" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
              </button>
            </div>
          </div>
          <div class="form-item">
            <label class="form-label">确认新密码</label>
            <div class="input-wrapper">
              <input :type="showConfirmPassword ? 'text' : 'password'" class="form-input" v-model="passwordForm.confirm" placeholder="请再次输入新密码" />
              <button type="button" class="toggle-eye" @click="showConfirmPassword = !showConfirmPassword">
                <svg v-if="!showConfirmPassword" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
              </button>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closePasswordDialog">取消</button>
          <button class="btn btn-primary" @click="submitChangePassword" :disabled="passwordLoading">
            {{ passwordLoading ? '修改中...' : '确认修改' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getPerformance, getUnreadNotifications, changePassword } from '@/api/index'

const router = useRouter()
const loading = ref(true)
const workerName = ref('维修员')
const unreadCount = ref(0)
let pollTimer = null

const perf = ref({
  today_orders: 0,
  month_orders: 0,
  // avg_star: 0,        // 【待开发】好评率功能
  // settlement_estimate: 0,  // 【待开发】总结算功能
})

// 修改密码相关
const showPasswordDialog = ref(false)
const passwordLoading = ref(false)
const passwordForm = ref({
  old: '',
  new: '',
  confirm: '',
})
const showOldPassword = ref(false)
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)

// Toast 提示
const showToast = (msg) => {
  const toast = document.createElement('div')
  toast.className = 'toast'
  toast.textContent = msg
  toast.style.cssText = `
    position: fixed;
    left: 50%;
    bottom: 80px;
    transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.8);
    color: #fff;
    padding: 10px 20px;
    border-radius: 6px;
    font-size: 14px;
    z-index: 9999;
  `
  document.body.appendChild(toast)
  setTimeout(() => toast.remove(), 2500)
}

async function fetchUnreadCount() {
  try {
    const data = await getUnreadNotifications()
    unreadCount.value = data.unread_count || 0
  } catch (e) {
    console.error('未读通知加载失败:', e)
  }
}

function goToNotifications() {
  router.push('/notifications')
}

onMounted(async () => {
  try {
    const raw = localStorage.getItem('worker_user')
    if (raw) {
      const u = JSON.parse(raw)
      workerName.value = u.name || u.user_id || '维修员'
    }
  } catch {}

  try {
    const data = await getPerformance()
    if (data) {
      perf.value = data
      // 性能 API 返回的 name 更可靠（来自 workers 表）
      if (data.name) {
        workerName.value = data.name
      }
    }
  } catch (e) {
    console.error('绩效加载失败:', e)
  } finally {
    loading.value = false
  }

  // 获取未读通知
  await fetchUnreadCount()

  // 每30秒轮询一次未读通知
  pollTimer = setInterval(fetchUnreadCount, 30000)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }
})

function handleLogout() {
  localStorage.removeItem('worker_token')
  localStorage.removeItem('worker_user')
  router.replace('/login')
}

function openChangePassword() {
  passwordForm.value = { old: '', new: '', confirm: '' }
  showPasswordDialog.value = true
}

function closePasswordDialog() {
  showPasswordDialog.value = false
}

async function submitChangePassword() {
  if (!passwordForm.value.old) {
    showToast('请输入原密码')
    return
  }
  if (!passwordForm.value.new || passwordForm.value.new.length < 6) {
    showToast('新密码至少6位')
    return
  }
  if (passwordForm.value.new !== passwordForm.value.confirm) {
    showToast('两次输入的新密码不一致')
    return
  }

  passwordLoading.value = true
  try {
    await changePassword(passwordForm.value.old, passwordForm.value.new)
    showToast('密码修改成功')
    closePasswordDialog()
  } catch (e) {
    showToast(e.msg || '修改失败')
  } finally {
    passwordLoading.value = false
  }
}
</script>

<style scoped>
.home-page {
  padding: 0 16px 24px;
  max-width: 480px;
  margin: 0 auto;
}

/* ── 顶栏 ── */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 0 14px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.header-logo {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #FF6B00, #CC5500);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 0 16px rgba(255, 107, 0, 0.25);
}
.header-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
}
.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.btn-notification {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color var(--duration-fast), color var(--duration-fast);
  position: relative;
  color: var(--color-text-dim);
}
.btn-notification:active {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.notification-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  background: var(--color-danger);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  box-shadow: 0 0 0 2px var(--color-bg);
}
.btn-logout {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color var(--duration-fast), color var(--duration-fast);
}
.btn-logout:active {
  border-color: var(--color-danger);
  color: var(--color-danger);
}
.logout-icon {
  font-size: 18px;
  color: var(--color-text-dim);
}

/* ── 绩效卡片 ── */
.stats-grid {
  display: grid;
  /* 【待开发】好评率和总结算恢复后改回 1fr 1fr 1fr 1fr */
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 18px;
}
.stat-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 16px;
  text-align: center;
  position: relative;
  overflow: hidden;
}
.sc-bg-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  border-radius: 0 0 2px 2px;
}
.sc-orange .sc-bg-bar { background: var(--color-primary); }
.sc-blue .sc-bg-bar { background: var(--color-info); }
.sc-green .sc-bg-bar { background: var(--color-success); }
.sc-purple .sc-bg-bar { background: #8e44ad; }

.sc-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text);
  margin: 4px 0 2px;
  position: relative;
  z-index: 1;
}
.sc-value small {
  font-size: 16px;
  color: var(--color-warning);
}
.sc-label {
  font-size: 11px;
  color: var(--color-text-dim);
  letter-spacing: 1px;
  text-transform: uppercase;
  position: relative;
  z-index: 1;
}

/* 仪表刻度装饰 */
.sc-gauge {
  position: absolute;
  bottom: 6px;
  left: 8px;
  right: 8px;
  height: 8px;
  opacity: 0.06;
  display: flex;
  align-items: flex-end;
}
.gauge-ticks {
  display: block;
  width: 100%;
  height: 100%;
  background: repeating-linear-gradient(
    90deg,
    var(--color-text),
    var(--color-text) 1px,
    transparent 1px,
    transparent 8px
  );
}

/* ── 快捷入口 ── */
.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.action-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: transform var(--duration-fast), border-color var(--duration-fast);
  position: relative;
}
.action-card:active {
  transform: scale(0.98);
}
.action-primary {
  border-left: 4px solid var(--color-primary);
}
.action-icon {
  flex-shrink: 0;
  color: var(--color-text-dim);
  transition: color var(--duration-fast);
}
.action-primary .action-icon {
  color: var(--color-primary);
  filter: drop-shadow(0 0 6px rgba(255, 107, 0, 0.3));
}
.action-info {
  flex: 1;
  min-width: 0;
}
.action-title {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
}
.action-desc {
  display: block;
  font-size: 12px;
  color: var(--color-text-dim);
  margin-top: 2px;
}
.action-arrow {
  font-size: 18px;
  color: var(--color-text-dim);
  flex-shrink: 0;
  font-family: var(--font-mono);
}

/* ── 加载 ── */
.loading-state {
  text-align: center;
  padding: 40px 0;
  color: var(--color-text-dim);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}
.load-ring {
  width: 24px;
  height: 24px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 弹窗 ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}
.modal-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 360px;
  overflow: hidden;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
}
.modal-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
}
.modal-close {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-bg);
  border: none;
  font-size: 18px;
  color: var(--color-text-dim);
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal-body {
  padding: 20px;
}
.modal-footer {
  display: flex;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid var(--color-border);
}
.btn {
  flex: 1;
  height: 44px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 14px;
  font-weight: 500;
}
.btn-primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}
.btn-primary:disabled {
  opacity: 0.6;
}
.btn-secondary {
  background: var(--color-bg);
}
.form-item {
  margin-bottom: 16px;
}
.form-item:last-child {
  margin-bottom: 0;
}
.form-label {
  display: block;
  font-size: 13px;
  color: var(--color-text-dim);
  margin-bottom: 6px;
}
.input-wrapper {
  position: relative;
}
.form-input {
  width: 100%;
  height: 44px;
  padding: 0 44px 0 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 14px;
  box-sizing: border-box;
}
.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
}
.toggle-eye {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--color-text-dim);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.toggle-eye:hover {
  color: var(--color-text);
}
</style>
