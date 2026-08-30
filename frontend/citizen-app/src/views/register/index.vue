<!--
  城市设施报修 · 市民端 - 注册页
-->
<template>
  <div class="register-page">
    <div class="light-beams">
      <div class="beam b1"></div>
      <div class="beam b2"></div>
      <div class="beam b3"></div>
    </div>

    <div class="register-content">
      <div class="brand">
        <div class="brand-mark mono">CR</div>
        <h2 class="brand-title">创建账号</h2>
        <p class="brand-tag">先注册，再登录</p>
      </div>

      <form class="register-form" @submit.prevent="handleRegister">
        <div class="input-wrap">
          <input v-model="form.username" type="text" placeholder="用户名（2-64位）" class="input" autocomplete="username" required />
          <span class="input-line"></span>
        </div>
        <div class="input-wrap">
          <input v-model="form.nickname" type="text" placeholder="昵称（选填，默认同用户名）" class="input" />
          <span class="input-line"></span>
        </div>
        <div class="input-wrap">
          <input v-model="form.phone" type="tel" maxlength="11" placeholder="手机号" class="input" autocomplete="tel" required />
          <span class="input-line"></span>
        </div>
        <div class="sms-row">
          <div class="sms-hint">注册手机号用于接收验证码</div>
          <button class="sms-btn" type="button" :disabled="smsSending || smsCountdown > 0 || !canSendSms" @click="handleSendCode">
            <span v-if="smsSending" class="loading-ring"></span>
            <span v-else-if="smsCountdown > 0">{{ smsCountdown }}s</span>
            <span v-else>获取验证码</span>
          </button>
        </div>
        <div class="input-wrap">
          <input v-model="form.password" type="password" placeholder="密码（至少6位）" class="input" autocomplete="new-password" required />
          <span class="input-line"></span>
        </div>
        <div class="input-wrap">
          <input v-model="form.password2" type="password" placeholder="确认密码" class="input" autocomplete="new-password" required @keyup.enter="handleRegister" />
          <span class="input-line"></span>
        </div>
        <div class="input-wrap">
          <input v-model="form.verifyCode" type="text" maxlength="6" placeholder="短信验证码" class="input" autocomplete="one-time-code" required />
          <span class="input-line"></span>
        </div>

        <div v-if="form.password" class="strength-bar">
          <div class="strength-fill" :class="strengthClass" :style="{ width: strengthPercent + '%' }"></div>
        </div>

        <div v-if="errorMsg" class="error-msg">
          <span class="error-dot"></span>
          {{ errorMsg }}
        </div>

        <button type="submit" class="btn-register" :disabled="!canSubmit || loading">
          <span v-if="loading" class="loading-ring"></span>
          <span v-else>注册</span>
        </button>
      </form>

      <router-link to="/login" class="link-login">← 返回登录</router-link>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { register, sendSmsCode } from '@/api/index'

const router = useRouter()
const loading = ref(false)
const smsSending = ref(false)
const smsCountdown = ref(0)
const errorMsg = ref('')
const form = reactive({ username: '', nickname: '', phone: '', password: '', password2: '', verifyCode: '' })
let countdownTimer = null

const canSendSms = computed(() => form.phone.length === 11)
const canSubmit = computed(() =>
  form.username.length >= 2 &&
  form.password.length >= 6 &&
  form.password === form.password2 &&
  form.phone.length === 11 &&
  form.verifyCode.length >= 4
)

const strengthPercent = computed(() => {
  const p = form.password
  if (!p) return 0
  let score = 20
  if (p.length >= 8) score += 25
  if (/[A-Z]/.test(p)) score += 15
  if (/[0-9]/.test(p)) score += 15
  if (/[^A-Za-z0-9]/.test(p)) score += 15
  if (p.length >= 12) score += 10
  return Math.min(100, score)
})

const strengthClass = computed(() => {
  if (strengthPercent.value <= 30) return 'weak'
  if (strengthPercent.value <= 65) return 'medium'
  return 'strong'
})

async function handleSendCode() {
  errorMsg.value = ''
  if (!canSendSms.value) {
    errorMsg.value = '请输入正确的手机号'
    return
  }
  smsSending.value = true
  try {
    await sendSmsCode(form.phone, 'register')
    smsCountdown.value = 60
    countdownTimer = setInterval(() => {
      smsCountdown.value--
      if (smsCountdown.value <= 0) {
        clearInterval(countdownTimer)
        countdownTimer = null
      }
    }, 1000)
  } catch (e) {
    errorMsg.value = e.message || '验证码发送失败'
  } finally {
    smsSending.value = false
  }
}

async function handleRegister() {
  errorMsg.value = ''
  if (!canSubmit.value) {
    if (form.password !== form.password2) errorMsg.value = '两次输入的密码不一致'
    else if (form.password.length < 6) errorMsg.value = '密码至少需要6位'
    else if (form.username.length < 2) errorMsg.value = '用户名至少需要2位'
    else if (form.phone.length !== 11) errorMsg.value = '请输入正确的手机号'
    else if (form.verifyCode.length < 4) errorMsg.value = '请输入短信验证码'
    return
  }
  loading.value = true
  try {
    const data = await register({
      username: form.username,
      password: form.password,
      nickname: form.nickname || form.username,
      phone: form.phone,
      verify_code: form.verifyCode,
    })
    localStorage.setItem('citizen_token', data.token)
    localStorage.setItem('citizen_user', JSON.stringify(data))
    router.replace('/home')
  } catch (e) {
    errorMsg.value = e.message || '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

onBeforeUnmount(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<style scoped>
.register-page { min-height: 100vh; min-height: 100dvh; display: flex; align-items: center; justify-content: center; padding: 40px 24px; position: relative; overflow: hidden; background: linear-gradient(180deg, #0a0c12 0%, #12151d 40%, #181b26 100%); }
.light-beams { position: absolute; inset: 0; pointer-events: none; }
.beam { position: absolute; bottom: -100px; width: 1px; background: linear-gradient(to top, rgba(255, 137, 34, 0.15), rgba(255, 137, 34, 0.04) 60%, transparent); animation: beam-up 8s ease-in-out infinite; }
.b1 { left: 25%; height: 60%; animation-delay: 0s; }
.b2 { left: 55%; height: 50%; animation-delay: 2.5s; }
.b3 { left: 78%; height: 65%; animation-delay: 5s; }
@keyframes beam-up { 0%, 100% { opacity: 0.3; transform: translateY(0); } 50% { opacity: 0.7; transform: translateY(-20px); } }
.register-content { position: relative; z-index: 1; width: 100%; max-width: 340px; display: flex; flex-direction: column; align-items: center; gap: 28px; }
.brand { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.brand-mark { width: 56px; height: 56px; background: linear-gradient(135deg, var(--color-amber), #cc6600); border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: 700; color: #fff; box-shadow: var(--shadow-glow-amber); }
.brand-title { font-size: 20px; font-weight: 600; letter-spacing: 2px; color: var(--color-text); }
.brand-tag { font-size: 12px; color: var(--color-text-dim); letter-spacing: 2px; }
.register-form { width: 100%; display: flex; flex-direction: column; gap: 16px; }
.input-wrap { position: relative; }
.input { width: 100%; height: 48px; padding: 0 0 0 4px; border: none; border-bottom: 1px solid var(--color-border); background: transparent; font-size: 14px; color: var(--color-text); outline: none; transition: border-color var(--duration-normal); }
.input::placeholder { color: var(--color-text-dim); }
.input:focus { border-bottom-color: var(--color-amber); }
.input-line { position: absolute; bottom: 0; left: 0; width: 0; height: 1px; background: var(--color-amber); transition: width var(--duration-slow) var(--ease-out-expo); box-shadow: var(--color-amber-glow); }
.input:focus ~ .input-line { width: 100%; }
.sms-row { display: flex; gap: 12px; align-items: center; }
.sms-hint { flex: 1; font-size: 12px; color: var(--color-text-dim); line-height: 1.3; }
.sms-btn { flex-shrink: 0; height: 48px; padding: 0 14px; border-radius: var(--radius-md); border: 1px solid var(--color-amber); background: transparent; color: var(--color-amber); font-size: 13px; white-space: nowrap; }
.sms-btn:disabled { opacity: 0.5; }
.strength-bar { height: 3px; border-radius: 2px; background: var(--color-border); overflow: hidden; }
.strength-fill { height: 100%; border-radius: 2px; transition: width 0.3s, background 0.3s; }
.strength-fill.weak { background: var(--color-red); }
.strength-fill.medium { background: var(--color-yellow); }
.strength-fill.strong { background: var(--color-green); box-shadow: var(--color-green-glow); }
.error-msg { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--color-red); padding: 2px 0; }
.error-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--color-red); box-shadow: 0 0 6px var(--color-red); flex-shrink: 0; }
.btn-register { width: 100%; height: 50px; border-radius: var(--radius-md); background: linear-gradient(135deg, #e67a1e, #cc6600); color: #fff; font-size: 15px; font-weight: 600; margin-top: 4px; box-shadow: var(--shadow-glow-amber); }
.btn-register:disabled { opacity: 0.5; }
.loading-ring { width: 20px; height: 20px; border: 2px solid rgba(255,255,255,0.25); border-top-color: #fff; border-radius: 50%; display: inline-block; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.link-login { font-size: 13px; color: var(--color-text-dim); letter-spacing: 1px; padding: 8px 16px; transition: color var(--duration-fast); }
.link-login:hover { color: var(--color-text-secondary); }
</style>

