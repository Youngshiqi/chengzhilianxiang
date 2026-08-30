<!--
  城市设施报修 · 维修工端 — 登录页
  重工仪表：工业终端 — 扫描线背景 + 铆钉表单 + 安全橙操作
-->
<template>
  <div class="login-page">
    <!-- 扫描线背景 -->
    <div class="scanlines"></div>

    <div class="login-content">
      <!-- 品牌区 -->
      <div class="brand">
        <div class="brand-hex">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="9" />
            <circle cx="12" cy="12" r="3" />
            <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" />
          </svg>
        </div>
        <h1 class="brand-name">CityRepair</h1>
        <p class="brand-sub">维修工专用终端</p>
      </div>

      <!-- 登录表单卡片 -->
      <form class="login-card" @submit.prevent="handleLogin">
        <!-- 铆钉四角 -->
        <span class="rivet r1"></span>
        <span class="rivet r2"></span>
        <span class="rivet r3"></span>
        <span class="rivet r4"></span>

        <div class="input-group">
          <span class="input-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </span>
          <input
            v-model="form.username"
            type="text"
            placeholder="用户名"
            class="input"
            autocomplete="username"
          />
          <span class="input-bar"></span>
        </div>

        <div class="input-group">
          <span class="input-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="3" y="11" width="18" height="11" rx="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </span>
          <input
            v-model="form.password"
            type="password"
            placeholder="密码"
            class="input"
            autocomplete="current-password"
            @keyup.enter="handleLogin"
          />
          <span class="input-bar"></span>
        </div>

        <!-- 错误提示 -->
        <div v-if="errorMsg" class="error-msg">
          <span class="error-dot"></span>
          {{ errorMsg }}
        </div>

        <!-- 登录按钮 -->
        <button type="submit" class="btn-login" :disabled="loading">
          <span v-if="loading" class="btn-spinner"></span>
          <span v-else class="btn-text">进 入 终 端</span>
        </button>
      </form>

      <!-- 底部提示 + 危险条纹 -->
      <div class="bottom-hint">
        <div class="hazard-stripe"></div>
        <span class="hint-text">仅限维修工角色账号登录</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '@/api/index'

const router = useRouter()
const loading = ref(false)
const errorMsg = ref('')
const form = reactive({ username: '', password: '' })

// GPS 坐标（三级降级：高德定位SDK → 浏览器GPS → 后端IP定位 → 默认长沙中心）
const gps = ref({ lng: undefined, lat: undefined })

function acquireGPS() {
  // 优先使用高德 Geolocation SDK（国内精度更高）
  if (window.AMap) {
    AMap.plugin('AMap.Geolocation', () => {
      const geo = new AMap.Geolocation({
        enableHighAccuracy: true,
        timeout: 10000,
        noIpLocate: 0,
        noGeoLocation: 0,
      })
      geo.getCurrentPosition((status, result) => {
        if (status === 'complete' && result.position) {
          gps.value.lng = result.position.lng
          gps.value.lat = result.position.lat
        }
        // 失败时不处理，后端降级为 IP 定位
      })
    })
    return
  }

  // 降级：浏览器原生 Geolocation
  if (!navigator.geolocation) return
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      gps.value.lng = pos.coords.longitude
      gps.value.lat = pos.coords.latitude
    },
    () => {
      // GPS 失败，后端将降级为 IP 定位
    },
    { enableHighAccuracy: true, timeout: 8000 },
  )
}

onMounted(() => {
  acquireGPS()
})

async function handleLogin() {
  errorMsg.value = ''
  if (!form.username || !form.password) {
    errorMsg.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  try {
    const data = await login(form.username, form.password, gps.value.lng, gps.value.lat)
    if (data.role !== 'worker') {
      errorMsg.value = '该账号非维修工角色，无法登录'
      return
    }
    localStorage.setItem('worker_token', data.token)
    localStorage.setItem('worker_user', JSON.stringify(data))
    router.replace('/home')
  } catch (e) {
    errorMsg.value = e.message || '登录失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh; min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  position: relative;
  overflow: hidden;
  background: linear-gradient(180deg, #050709 0%, #0a0d12 40%, #0f131a 100%);
}

/* ── 扫描线 ── */
.scanlines {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(255, 255, 255, 0.008) 2px,
    rgba(255, 255, 255, 0.008) 4px
  );
  z-index: 0;
}

.login-content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 340px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
}

/* ── 品牌 ── */
.brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.brand-hex {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #FF6B00, #CC5500);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: var(--shadow-glow-orange);
  position: relative;
}
.brand-hex::after {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 18px;
  border: 1px solid rgba(255, 107, 0, 0.3);
}
.brand-name {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 600;
  letter-spacing: 4px;
  color: var(--color-text);
}
.brand-sub {
  font-size: 12px;
  color: var(--color-text-dim);
  letter-spacing: 2px;
}

/* ── 表单卡片 ── */
.login-card {
  width: 100%;
  background: var(--color-surface);
  border: 1px solid var(--color-border-active);
  border-radius: var(--radius-lg);
  padding: 28px 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
}

/* 铆钉四角 */
.rivet {
  position: absolute;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-border-active);
  border: 1px solid var(--color-text-dim);
  z-index: 1;
}
.r1 { top: 8px; left: 8px; }
.r2 { top: 8px; right: 8px; }
.r3 { bottom: 8px; left: 8px; }
.r4 { bottom: 8px; right: 8px; }

/* ── 输入框 ── */
.input-group {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
}
.input-icon {
  flex-shrink: 0;
  color: var(--color-text-dim);
  transition: color var(--duration-normal);
}
.input-group:focus-within .input-icon {
  color: var(--color-primary);
}
.input {
  flex: 1;
  height: 44px;
  border: none;
  border-bottom: 2px solid var(--color-border);
  background: transparent;
  font-size: 15px;
  color: var(--color-text);
  outline: none;
  padding: 0 4px;
  transition: border-color var(--duration-normal);
}
.input::placeholder {
  color: var(--color-text-dim);
}
.input-bar {
  position: absolute;
  bottom: 0;
  left: 28px;
  right: 0;
  height: 2px;
  background: var(--color-primary);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform var(--duration-slow) var(--ease-out-expo);
}
.input:focus {
  border-bottom-color: transparent;
}
.input:focus ~ .input-bar {
  transform: scaleX(1);
}

/* ── 错误 ── */
.error-msg {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-danger);
  padding: 0 4px;
}
.error-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-danger);
  box-shadow: 0 0 6px var(--color-danger);
  flex-shrink: 0;
}

/* ── 登录按钮 ── */
.btn-login {
  width: 100%;
  height: 50px;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, #FF6B00, #E05500);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 3px;
  margin-top: 4px;
  box-shadow: var(--shadow-glow-orange);
  transition: transform var(--duration-fast), box-shadow var(--duration-fast);
  position: relative;
  overflow: hidden;
}
.btn-login::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
  transition: left 0.6s;
}
.btn-login:active:not(:disabled)::before {
  left: 100%;
}
.btn-login:active:not(:disabled) {
  transform: scale(0.97);
}
.btn-login:disabled {
  opacity: 0.5;
}
.btn-text {
  position: relative;
  z-index: 1;
}

.btn-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  display: inline-block;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 底部提示 ── */
.bottom-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.hazard-stripe {
  width: 120px;
  height: 4px;
  background: repeating-linear-gradient(
    90deg,
    var(--color-warning),
    var(--color-warning) 10px,
    var(--color-bg) 10px,
    var(--color-bg) 20px
  );
  border-radius: 1px;
  opacity: 0.5;
}
.hint-text {
  font-size: 12px;
  color: var(--color-text-dim);
  letter-spacing: 1px;
}
</style>
