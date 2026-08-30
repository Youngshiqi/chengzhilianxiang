<!--
  城市设施报修 · 市民端 - 登录页
-->
<template>
  <div class="login-page" ref="pageRef">
    <canvas class="particle-canvas" ref="canvasRef"></canvas>

    <div class="aurora-layer">
      <div class="aurora aurora-1"></div>
      <div class="aurora aurora-2"></div>
      <div class="aurora aurora-3"></div>
    </div>

    <div class="twilight-sky">
      <div class="sky-gradient"></div>
      <div class="sky-stars">
        <span v-for="i in 40" :key="i" class="star" :style="starStyle(i)"></span>
      </div>
    </div>

    <div class="city-background">
      <div class="city-layer layer-far">
        <svg viewBox="0 0 800 200" preserveAspectRatio="none">
          <rect x="10" y="90" width="25" height="110" fill="#0d1018"/>
          <rect x="45" y="110" width="20" height="90" fill="#0a0d14"/>
          <rect x="75" y="60" width="30" height="140" fill="#0e1119"/>
          <rect x="115" y="100" width="22" height="100" fill="#0b0e15"/>
          <rect x="150" y="40" width="35" height="160" fill="#0c1018"/>
          <rect x="195" y="80" width="25" height="120" fill="#0d1018"/>
          <rect x="230" y="50" width="28" height="150" fill="#0a0d14"/>
          <rect x="270" y="95" width="22" height="105" fill="#0e1119"/>
          <rect x="305" y="30" width="32" height="170" fill="#0b0e15"/>
          <rect x="350" y="70" width="24" height="130" fill="#0c1018"/>
          <rect x="385" y="45" width="30" height="155" fill="#0d1018"/>
          <rect x="425" y="85" width="20" height="115" fill="#0a0d14"/>
          <rect x="458" y="55" width="28" height="145" fill="#0e1119"/>
          <rect x="498" y="100" width="25" height="100" fill="#0b0e15"/>
          <rect x="535" y="35" width="35" height="165" fill="#0c1018"/>
          <rect x="580" y="75" width="26" height="125" fill="#0d1018"/>
          <rect x="618" y="50" width="30" height="150" fill="#0a0d14"/>
          <rect x="660" y="90" width="24" height="110" fill="#0e1119"/>
          <rect x="698" y="40" width="32" height="160" fill="#0b0e15"/>
          <rect x="745" y="80" width="30" height="120" fill="#0c1018"/>
        </svg>
      </div>

      <div class="city-layer layer-mid">
        <svg viewBox="0 0 800 220" preserveAspectRatio="none">
          <rect x="5" y="70" width="35" height="150" rx="2" fill="#121623"/>
          <rect x="50" y="100" width="28" height="120" rx="1" fill="#0f131e"/>
          <rect x="90" y="40" width="40" height="180" rx="2" fill="#141827"/>
          <rect x="145" y="80" width="30" height="140" rx="1" fill="#111521"/>
          <rect x="188" y="20" width="45" height="200" rx="2" fill="#131725"/>
          <rect x="248" y="60" width="32" height="160" rx="1" fill="#10141f"/>
          <rect x="295" y="35" width="38" height="185" rx="2" fill="#141827"/>
          <rect x="350" y="90" width="28" height="130" rx="1" fill="#121623"/>
          <rect x="395" y="15" width="50" height="205" rx="2" fill="#0f131e"/>
          <rect x="460" y="55" width="35" height="165" rx="1" fill="#141827"/>
          <rect x="510" y="85" width="30" height="135" rx="1" fill="#111521"/>
          <rect x="555" y="25" width="42" height="195" rx="2" fill="#131725"/>
          <rect x="615" y="65" width="32" height="155" rx="1" fill="#10141f"/>
          <rect x="662" y="45" width="38" height="175" rx="2" fill="#141827"/>
          <rect x="718" y="75" width="35" height="145" rx="1" fill="#121623"/>
          <rect x="765" y="50" width="30" height="170" rx="1" fill="#0f131e"/>
        </svg>
      </div>

      <div class="city-layer layer-near">
        <svg viewBox="0 0 800 240" preserveAspectRatio="none">
          <g class="building building-1">
            <rect x="20" y="50" width="50" height="190" rx="3" fill="#181c2a"/>
            <g class="windows">
              <rect v-for="i in 24" :key="'w1-' + i"
                :x="28 + ((i - 1) % 4) * 10"
                :y="65 + Math.floor((i - 1) / 4) * 18"
                width="6" height="10" rx="1"
                :class="'window ' + (isWindowLit(1, i) ? 'lit' : '')"/>
            </g>
          </g>
          <g class="building building-2">
            <rect x="85" y="80" width="40" height="160" rx="2" fill="#151926"/>
            <g class="windows">
              <rect v-for="i in 20" :key="'w2-' + i"
                :x="93 + ((i - 1) % 4) * 8"
                :y="95 + Math.floor((i - 1) / 4) * 16"
                width="5" height="9" rx="1"
                :class="'window ' + (isWindowLit(2, i) ? 'lit' : '')"/>
            </g>
          </g>
          <g class="building building-3">
            <rect x="140" y="20" width="60" height="220" rx="4" fill="#1a1f30"/>
            <g class="windows">
              <rect v-for="i in 44" :key="'w3-' + i"
                :x="150 + ((i - 1) % 5) * 10"
                :y="35 + Math.floor((i - 1) / 5) * 16"
                width="6" height="10" rx="1"
                :class="'window ' + (isWindowLit(3, i) ? 'lit' : '')"/>
            </g>
          </g>
          <g class="building building-4">
            <rect x="215" y="60" width="45" height="180" rx="2" fill="#161a28"/>
            <g class="windows">
              <rect v-for="i in 24" :key="'w4-' + i"
                :x="223 + ((i - 1) % 4) * 9"
                :y="75 + Math.floor((i - 1) / 4) * 16"
                width="5" height="9" rx="1"
                :class="'window ' + (isWindowLit(4, i) ? 'lit' : '')"/>
            </g>
          </g>
          <g class="building building-5">
            <rect x="275" y="35" width="55" height="205" rx="3" fill="#191e2f"/>
            <g class="windows">
              <rect v-for="i in 36" :key="'w5-' + i"
                :x="284 + ((i - 1) % 5) * 9"
                :y="50 + Math.floor((i - 1) / 5) * 16"
                width="6" height="10" rx="1"
                :class="'window ' + (isWindowLit(5, i) ? 'lit' : '')"/>
            </g>
          </g>
          <g class="building building-6">
            <rect x="345" y="70" width="38" height="170" rx="2" fill="#151926"/>
            <g class="windows">
              <rect v-for="i in 20" :key="'w6-' + i"
                :x="353 + ((i - 1) % 4) * 7"
                :y="85 + Math.floor((i - 1) / 4) * 15"
                width="5" height="8" rx="1"
                :class="'window ' + (isWindowLit(6, i) ? 'lit' : '')"/>
            </g>
          </g>
          <g class="building building-7">
            <rect x="400" y="10" width="70" height="230" rx="4" fill="#1b2033"/>
            <g class="windows">
              <rect v-for="i in 56" :key="'w7-' + i"
                :x="410 + ((i - 1) % 6) * 9"
                :y="28 + Math.floor((i - 1) / 6) * 15"
                width="6" height="9" rx="1"
                :class="'window ' + (isWindowLit(7, i) ? 'lit' : '')"/>
            </g>
          </g>
          <g class="building building-8">
            <rect x="485" y="55" width="42" height="185" rx="3" fill="#171b2b"/>
            <g class="windows">
              <rect v-for="i in 28" :key="'w8-' + i"
                :x="493 + ((i - 1) % 4) * 8"
                :y="70 + Math.floor((i - 1) / 4) * 16"
                width="5" height="9" rx="1"
                :class="'window ' + (isWindowLit(8, i) ? 'lit' : '')"/>
            </g>
          </g>
          <g class="building building-9">
            <rect x="545" y="25" width="60" height="215" rx="3" fill="#1a1f30"/>
            <g class="windows">
              <rect v-for="i in 44" :key="'w9-' + i"
                :x="555 + ((i - 1) % 5) * 10"
                :y="40 + Math.floor((i - 1) / 5) * 16"
                width="6" height="10" rx="1"
                :class="'window ' + (isWindowLit(9, i) ? 'lit' : '')"/>
            </g>
          </g>
          <g class="building building-10">
            <rect x="620" y="75" width="35" height="165" rx="2" fill="#151926"/>
            <g class="windows">
              <rect v-for="i in 20" :key="'w10-' + i"
                :x="628 + ((i - 1) % 4) * 7"
                :y="90 + Math.floor((i - 1) / 4) * 15"
                width="5" height="8" rx="1"
                :class="'window ' + (isWindowLit(10, i) ? 'lit' : '')"/>
            </g>
          </g>
          <g class="building building-11">
            <rect x="670" y="45" width="52" height="195" rx="3" fill="#181c2a"/>
            <g class="windows">
              <rect v-for="i in 36" :key="'w11-' + i"
                :x="679 + ((i - 1) % 5) * 9"
                :y="60 + Math.floor((i - 1) / 5) * 16"
                width="6" height="10" rx="1"
                :class="'window ' + (isWindowLit(11, i) ? 'lit' : '')"/>
            </g>
          </g>
          <g class="building building-12">
            <rect x="735" y="65" width="45" height="175" rx="2" fill="#161a28"/>
            <g class="windows">
              <rect v-for="i in 28" :key="'w12-' + i"
                :x="743 + ((i - 1) % 4) * 9"
                :y="80 + Math.floor((i - 1) / 4) * 16"
                width="5" height="9" rx="1"
                :class="'window ' + (isWindowLit(12, i) ? 'lit' : '')"/>
            </g>
          </g>
        </svg>
        <div class="city-glow"></div>
      </div>
    </div>

    <div class="login-content">
      <div class="brand">
        <div class="brand-hex">
          <svg width="56" height="60" viewBox="0 0 52 56">
            <polygon points="26,2 48,14 48,38 26,50 4,38 4,14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
            <circle cx="26" cy="26" r="8" fill="currentColor" opacity="0.9"/>
            <circle cx="26" cy="26" r="14" fill="none" stroke="currentColor" stroke-width="0.5" opacity="0.3"/>
            <g class="repair-mark" transform="translate(26, 26)">
              <circle cx="0" cy="0" r="18" fill="none" stroke="rgba(255, 80, 80, 0.5)" stroke-width="1" stroke-dasharray="4 4">
                <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="20s" repeatCount="indefinite"/>
              </circle>
            </g>
          </svg>
          <div class="hex-ring ring-1"></div>
          <div class="hex-ring ring-2"></div>
        </div>
        <h1 class="brand-title mono">CityRepair</h1>
        <p class="brand-tag">城市设施 · 智能报修</p>
        <div class="brand-badges">
          <span class="badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
            安全可靠
          </span>
          <span class="badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
            快速响应
          </span>
        </div>
      </div>

      <form class="login-form" @submit.prevent="handleLogin">
        <div class="input-wrap">
          <div class="input-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="8" r="4"/>
              <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
            </svg>
          </div>
          <input v-model="form.username" type="text" placeholder="用户名" class="input" autocomplete="username" required />
          <span class="input-line"></span>
        </div>
        <div class="input-wrap">
          <div class="input-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="3" y="11" width="18" height="10" rx="2"/>
              <path d="M8 11V7a4 4 0 018 0v4"/>
            </svg>
          </div>
          <input v-model="form.password" type="password" placeholder="密码" class="input" autocomplete="current-password" required @keyup.enter="handleLogin" />
          <span class="input-line"></span>
        </div>

        <div v-if="errorMsg" class="error-msg">
          <span class="error-dot"></span>{{ errorMsg }}
        </div>

        <button type="submit" class="btn-login" :disabled="loading">
          <span class="btn-shine"></span>
          <span v-if="loading" class="btn-loading">
            <span class="loading-ring"></span>
          </span>
          <span v-else class="btn-text">
            <span class="btn-label">进入报修系统</span>
            <span class="btn-arrow">→</span>
          </span>
        </button>
      </form>

      <div class="phone-login-section">
        <div class="divider">
          <span class="divider-line"></span>
          <span class="divider-text">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/>
              <circle cx="12" cy="10" r="3"/>
            </svg>
            其他登录方式
          </span>
          <span class="divider-line"></span>
        </div>
        <button class="btn-phone-login" @click="showSmsDialog = true" type="button">
          <svg class="phone-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="5" y="2" width="14" height="20" rx="2"/>
            <path d="M12 18h.01"/>
          </svg>
          手机号验证码登录
        </button>
      </div>

      <div class="footer-links">
        <router-link to="/register" class="link-register">
          没有账号？<span class="link-register-text">创建账号</span>
          <span class="link-arrow">→</span>
        </router-link>
      </div>
    </div>

    <teleport to="body">
      <transition name="dialog-fade">
        <div v-if="showSmsDialog" class="sms-dialog-overlay" @click.self="showSmsDialog = false">
          <transition name="dialog-slide">
            <div class="sms-dialog" v-if="showSmsDialog">
              <div class="dialog-header">
                <div class="dialog-title-wrap">
                  <svg class="dialog-icon" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    <circle cx="12" cy="11" r="2" fill="currentColor"/>
                  </svg>
                  <h3 class="sms-dialog-title">手机号验证码登录</h3>
                </div>
                <button class="dialog-close" @click="showSmsDialog = false" type="button">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M18 6L6 18M6 6l12 12"/>
                  </svg>
                </button>
              </div>
              <div class="sms-input-group">
                <label class="sms-label">手机号</label>
                <input v-model="smsForm.phone" type="tel" maxlength="11" placeholder="请输入手机号" class="sms-input" autocomplete="tel" />
              </div>
              <div class="sms-input-group">
                <label class="sms-label">验证码</label>
                <div class="sms-code-row">
                  <input v-model="smsForm.code" type="text" maxlength="6" placeholder="请输入验证码" class="sms-input sms-code-input" autocomplete="one-time-code" @keyup.enter="handleSmsLogin" />
                  <button class="sms-send-btn" :disabled="smsSending || smsCountdown > 0" @click="handleSendCode" type="button">
                    <span v-if="smsSending" class="btn-loading"><span class="loading-ring"></span></span>
                    <span v-else-if="smsCountdown > 0">{{ smsCountdown }}s</span>
                    <span v-else>发送验证码</span>
                  </button>
                </div>
              </div>
              <div v-if="smsError" class="sms-error">{{ smsError }}</div>
              <div class="sms-dialog-btns">
                <button class="sms-btn-cancel" @click="showSmsDialog = false" type="button">取消</button>
                <button class="sms-btn-confirm" :disabled="smsLogging" @click="handleSmsLogin" type="button">
                  <span v-if="smsLogging" class="btn-loading"><span class="loading-ring"></span></span>
                  <span v-else>登录</span>
                </button>
              </div>
            </div>
          </transition>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup>
import { reactive, ref, onBeforeUnmount, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { login, sendSmsCode, smsLogin } from '@/api/index'

const router = useRouter()
const pageRef = ref(null)
const canvasRef = ref(null)

const loading = ref(false)
const errorMsg = ref('')
const form = reactive({ username: '', password: '' })
const showSmsDialog = ref(false)
const smsSending = ref(false)
const smsLogging = ref(false)
const smsError = ref('')
const smsCountdown = ref(0)
const smsForm = reactive({ phone: '', code: '' })

let countdownTimer = null
let animationId = null
let particles = []
let mouse = { x: null, y: null }

class Particle {
  constructor(canvas) {
    this.canvas = canvas
    this.reset()
  }

  reset() {
    this.x = Math.random() * this.canvas.width
    this.y = Math.random() * this.canvas.height
    this.speedX = (Math.random() - 0.5) * 0.8
    this.speedY = (Math.random() - 0.5) * 0.8
    this.size = Math.random() * 2 + 1
    this.baseAlpha = Math.random() * 0.4 + 0.1
    this.alpha = this.baseAlpha
    const rand = Math.random()
    this.hue = rand < 0.5 ? 35 : rand < 0.75 ? 0 : 210
  }

  update() {
    this.x += this.speedX
    this.y += this.speedY

    if (mouse.x !== null && mouse.y !== null) {
      const dx = mouse.x - this.x
      const dy = mouse.y - this.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 120) {
        const force = (120 - dist) / 120
        this.alpha = this.baseAlpha + force * 0.6
        this.x -= dx * force * 0.02
        this.y -= dy * force * 0.02
      } else {
        this.alpha = Math.max(this.baseAlpha, this.alpha - 0.01)
      }
    }

    if (this.x < 0 || this.x > this.canvas.width) this.speedX *= -1
    if (this.y < 0 || this.y > this.canvas.height) this.speedY *= -1
  }

  draw(ctx) {
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fillStyle = `hsla(${this.hue}, 85%, 65%, ${this.alpha})`
    ctx.fill()
  }
}

function initCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  const resize = () => {
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
  }
  resize()
  window.addEventListener('resize', resize)

  particles = Array.from({ length: 80 }, () => new Particle(canvas))

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    particles.forEach((p, i) => {
      p.update()
      p.draw(ctx)

      particles.slice(i + 1).forEach(p2 => {
        const dx = p.x - p2.x
        const dy = p.y - p2.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 100) {
          ctx.beginPath()
          ctx.strokeStyle = `hsla(${p.hue}, 85%, 65%, ${0.1 * (1 - dist / 100)})`
          ctx.lineWidth = 0.5
          ctx.moveTo(p.x, p.y)
          ctx.lineTo(p2.x, p2.y)
          ctx.stroke()
        }
      })

      if (mouse.x !== null && mouse.y !== null) {
        const dx = p.x - mouse.x
        const dy = p.y - mouse.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 150) {
          ctx.beginPath()
          ctx.strokeStyle = `hsla(${p.hue}, 85%, 65%, ${0.2 * (1 - dist / 150)})`
          ctx.lineWidth = 0.8
          ctx.moveTo(p.x, p.y)
          ctx.lineTo(mouse.x, mouse.y)
          ctx.stroke()
        }
      }
    })

    animationId = requestAnimationFrame(animate)
  }
  animate()

  const handleMouseMove = (e) => {
    mouse.x = e.clientX
    mouse.y = e.clientY
  }
  const handleMouseLeave = () => {
    mouse.x = null
    mouse.y = null
  }

  window.addEventListener('mousemove', handleMouseMove)
  window.addEventListener('mouseleave', handleMouseLeave)

  onBeforeUnmount(() => {
    window.removeEventListener('resize', resize)
    window.removeEventListener('mousemove', handleMouseMove)
    window.removeEventListener('mouseleave', handleMouseLeave)
    if (animationId) cancelAnimationFrame(animationId)
  })
}

onMounted(() => {
  initCanvas()
})

async function handleLogin() {
  errorMsg.value = ''
  if (!form.username || !form.password) {
    errorMsg.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  try {
    const data = await login(form.username, form.password)
    localStorage.setItem('citizen_token', data.token)
    localStorage.setItem('citizen_user', JSON.stringify(data))
    router.replace('/home')
  } catch (e) {
    errorMsg.value = e.message || '登录失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function handleSendCode() {
  smsError.value = ''
  if (!smsForm.phone || smsForm.phone.length !== 11) {
    smsError.value = '请输入正确的手机号'
    return
  }
  smsSending.value = true
  try {
    await sendSmsCode(smsForm.phone)
    smsCountdown.value = 60
    countdownTimer = setInterval(() => {
      smsCountdown.value--
      if (smsCountdown.value <= 0) {
        clearInterval(countdownTimer)
        countdownTimer = null
      }
    }, 1000)
  } catch (e) {
    smsError.value = e.message || '发送失败'
  } finally {
    smsSending.value = false
  }
}

async function handleSmsLogin() {
  smsError.value = ''
  if (!smsForm.phone || smsForm.phone.length !== 11) {
    smsError.value = '请输入正确的手机号'
    return
  }
  if (!smsForm.code) {
    smsError.value = '请输入验证码'
    return
  }
  smsLogging.value = true
  try {
    const data = await smsLogin(smsForm.phone, smsForm.code)
    localStorage.setItem('citizen_token', data.token)
    localStorage.setItem('citizen_user', JSON.stringify(data))
    router.replace('/home')
  } catch (e) {
    smsError.value = e.message || '登录失败'
  } finally {
    smsLogging.value = false
  }
}

onBeforeUnmount(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})

function starStyle(i) {
  const x = (i * 7) % 100
  const y = (i * 13) % 60
  const delay = (i * 0.17) % 3
  const size = (i % 3) * 0.5 + 1
  const opacity = (i % 5) * 0.1 + 0.2
  return {
    left: x + '%',
    top: y + '%',
    width: size + 'px',
    height: size + 'px',
    animationDelay: delay + 's',
    opacity
  }
}

function pseudoRandom(buildingId, windowId) {
  const seed = buildingId * 1000 + windowId
  const x = Math.sin(seed) * 10000
  return x - Math.floor(x)
}

function isWindowLit(buildingId, windowId) {
  return pseudoRandom(buildingId, windowId) < 0.18
}

function repairIconStyle(i) {
  const positions = [
    { left: '10%', top: '30%', delay: '0s' },
    { left: '30%', top: '20%', delay: '1s' },
    { left: '50%', top: '25%', delay: '2s' },
    { left: '70%', top: '18%', delay: '1.5s' },
    { left: '90%', top: '28%', delay: '0.5s' }
  ]
  return positions[i]
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: linear-gradient(180deg, #0a0c12 0%, #141720 35%, #1a1d29 60%, #0d0f14 100%);
  padding: 40px 24px;
}

.particle-canvas {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: auto;
}

.aurora-layer {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

.aurora {
  position: absolute;
  width: 200%;
  height: 200%;
  top: -50%;
  left: -50%;
  opacity: 0.18;
  filter: blur(70px);
  animation: aurora-drift 20s ease-in-out infinite;
}

.aurora-1 {
  background: radial-gradient(ellipse at 30% 30%, rgba(255, 137, 34, 0.5) 0%, transparent 50%);
  animation-delay: 0s;
}

.aurora-2 {
  background: radial-gradient(ellipse at 70% 20%, rgba(68, 138, 255, 0.35) 0%, transparent 45%);
  animation-delay: -5s;
}

.aurora-3 {
  background: radial-gradient(ellipse at 50% 40%, rgba(255, 80, 80, 0.25) 0%, transparent 40%);
  animation-delay: -10s;
}

@keyframes aurora-drift {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  25% { transform: translate(3%, 2%) rotate(3deg); }
  50% { transform: translate(-2%, 4%) rotate(-2deg); }
  75% { transform: translate(2%, -2%) rotate(2deg); }
}

.twilight-sky {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 1;
}

.sky-gradient {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 50% 0%, rgba(255, 137, 34, 0.1) 0%, transparent 50%),
    radial-gradient(ellipse at 30% 20%, rgba(68, 138, 255, 0.05) 0%, transparent 40%),
    radial-gradient(ellipse at 70% 10%, rgba(255, 80, 80, 0.06) 0%, transparent 35%);
}

.sky-stars {
  position: absolute;
  inset: 0;
}

.star {
  position: absolute;
  border-radius: 50%;
  background: #fff;
  animation: twinkle 3s ease-in-out infinite;
  box-shadow: 0 0 6px rgba(255, 255, 255, 0.5);
}

@keyframes twinkle {
  0%, 100% { opacity: 0.2; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.4); }
}

.city-background {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 280px;
  z-index: 2;
  pointer-events: none;
}

.city-layer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
}

.layer-far {
  height: 160px;
  opacity: 0.4;
  filter: blur(1px);
}

.layer-mid {
  height: 200px;
  opacity: 0.7;
  filter: blur(0.5px);
}

.layer-near {
  height: 260px;
  z-index: 3;
}

.city-glow {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 100px;
  background: radial-gradient(ellipse at 50% 100%, rgba(255, 137, 34, 0.15) 0%, transparent 60%);
  pointer-events: none;
}

.layer-near svg {
  overflow: visible;
}

.window {
  fill: rgba(30, 35, 50, 0.6);
}

.window.lit {
  fill: rgba(255, 193, 100, 0.9);
  box-shadow: 0 0 10px rgba(255, 193, 100, 0.6);
  animation: window-glow 3s ease-in-out infinite;
}

@keyframes window-glow {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
}

.window.lit:nth-child(3n) {
  animation-delay: 0.5s;
  fill: rgba(255, 220, 150, 0.95);
}

.window.lit:nth-child(5n) {
  animation-delay: 1s;
  fill: rgba(255, 170, 80, 0.9);
}

.window.lit:nth-child(7n) {
  animation-delay: 1.5s;
  fill: rgba(255, 140, 60, 0.85);
}

.repair-icons {
  position: absolute;
  inset: 0;
}

.repair-icon {
  position: absolute;
  animation: repair-float 4s ease-in-out infinite;
}

@keyframes repair-float {
  0%, 100% { transform: translateY(0) scale(1); opacity: 0.6; }
  50% { transform: translateY(-8px) scale(1.1); opacity: 1; }
}

.login-content {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
}

.brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.brand-hex {
  color: var(--color-amber);
  margin-bottom: 4px;
  filter: drop-shadow(0 0 25px rgba(255, 137, 34, 0.6));
  animation: hex-float 4s ease-in-out infinite;
  position: relative;
}

.hex-ring {
  position: absolute;
  inset: -18px;
  border: 1px solid rgba(255, 137, 34, 0.25);
  border-radius: 50%;
  animation: ring-pulse 3s ease-out infinite;
}

.ring-2 {
  inset: -30px;
  animation-delay: 1s;
}

@keyframes hex-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

@keyframes ring-pulse {
  0% { transform: scale(0.8); opacity: 0.6; }
  100% { transform: scale(1.5); opacity: 0; }
}

.brand-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 6px;
  color: var(--color-text);
  text-shadow: 0 0 40px rgba(255, 137, 34, 0.4);
}

.brand-tag {
  font-size: 13px;
  color: var(--color-text-dim);
  letter-spacing: 5px;
}

.brand-badges {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  font-size: 11px;
  color: var(--color-text-dim);
  background: rgba(255, 255, 255, 0.03);
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  letter-spacing: 1px;
}

.badge svg {
  color: var(--color-amber);
}

.login-form {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-wrap {
  position: relative;
}

.input-icon {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-dim);
  transition: color var(--duration-normal), transform var(--duration-normal);
  pointer-events: none;
}

.input {
  width: 100%;
  height: 54px;
  padding: 0 0 0 34px;
  border: none;
  border-bottom: 1px solid var(--color-border);
  background: transparent;
  font-size: 15px;
  color: var(--color-text);
  outline: none;
  transition: border-color var(--duration-normal);
}

.input::placeholder {
  color: var(--color-text-dim);
  transition: opacity var(--duration-normal);
}

.input:focus {
  border-bottom-color: var(--color-amber);
}

.input:focus::placeholder {
  opacity: 0.5;
}

.input:focus ~ .input-icon {
  color: var(--color-amber);
  transform: translateY(-50%) scale(1.15);
}

.input-line {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 1.5px;
  background: linear-gradient(90deg, var(--color-amber), rgba(255, 137, 34, 0.5));
  transition: width var(--duration-slow) var(--ease-out-expo);
  box-shadow: 0 0 12px rgba(255, 137, 34, 0.4);
}

.input:focus ~ .input-line {
  width: 100%;
}

.error-msg,
.sms-error {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-red);
  padding: 2px 0;
  animation: error-shake 0.4s ease-out;
}

@keyframes error-shake {
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-4px); }
  40%, 80% { transform: translateX(4px); }
}

.error-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-red);
  box-shadow: 0 0 8px var(--color-red);
  flex-shrink: 0;
  animation: error-pulse 1s ease-in-out infinite;
}

@keyframes error-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.3); opacity: 0.7; }
}

.btn-login {
  width: 100%;
  height: 54px;
  border-radius: 14px;
  background: linear-gradient(135deg, #e67a1e, #cc6600, #e67a1e);
  background-size: 200% 100%;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 3px;
  margin-top: 4px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 8px 30px rgba(255, 137, 34, 0.35);
  transition: all var(--duration-normal);
  animation: gradient-shift 8s ease-in-out infinite;
}

@keyframes gradient-shift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.btn-login:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: 0 12px 40px rgba(255, 137, 34, 0.5);
}

.btn-login:active:not(:disabled) {
  transform: translateY(-1px);
}

.btn-shine {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  animation: shine 3s ease-in-out infinite;
}

@keyframes shine {
  0% { left: -100%; }
  60%, 100% { left: 100%; }
}

.btn-text {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  position: relative;
  z-index: 1;
}

.btn-arrow {
  display: inline-block;
  transition: transform var(--duration-normal);
}

.btn-login:hover .btn-arrow {
  transform: translateX(6px);
}

.btn-loading,
.loading-ring {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.loading-ring {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(255, 255, 255, 0.25);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.phone-login-section {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
}

.divider {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-border), transparent);
  position: relative;
  overflow: hidden;
}

.divider-line::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 137, 34, 0.5), transparent);
  animation: line-drift 4s ease-in-out infinite;
}

@keyframes line-drift {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.divider-text {
  font-size: 12px;
  color: var(--color-text-dim);
  letter-spacing: 2px;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 6px;
}

.divider-text svg {
  color: var(--color-amber);
}

.btn-phone-login {
  width: 100%;
  height: 52px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: var(--color-text-secondary);
  font-size: 15px;
  letter-spacing: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  transition: all var(--duration-normal);
}

.btn-phone-login:hover {
  background: rgba(255, 137, 34, 0.08);
  border-color: rgba(255, 137, 34, 0.4);
  color: var(--color-amber);
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(255, 137, 34, 0.15);
}

.phone-icon {
  transition: transform var(--duration-normal);
}

.btn-phone-login:hover .phone-icon {
  transform: scale(1.15);
}

.sms-dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(10px);
  padding: 24px;
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}

.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.3s ease;
}

.dialog-slide-enter-from,
.dialog-slide-leave-to {
  opacity: 0;
  transform: scale(0.9) translateY(20px);
}

.dialog-slide-enter-active,
.dialog-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.sms-dialog {
  width: 100%;
  max-width: 360px;
  background: linear-gradient(180deg, #1e2230 0%, #141826 100%);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  padding: 26px 24px 22px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-shadow: 0 25px 70px rgba(0, 0, 0, 0.6), 0 0 50px rgba(255, 137, 34, 0.08);
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dialog-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.dialog-icon {
  color: var(--color-amber);
  filter: drop-shadow(0 0 8px rgba(255, 137, 34, 0.5));
}

.sms-dialog-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: 2px;
}

.dialog-close {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-dim);
  transition: all var(--duration-normal);
}

.dialog-close:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--color-text);
  transform: rotate(90deg);
}

.sms-input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sms-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  letter-spacing: 1px;
}

.sms-input {
  width: 100%;
  height: 52px;
  padding: 0 18px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--color-text);
  font-size: 15px;
  outline: none;
  transition: all var(--duration-normal);
}

.sms-input:focus {
  border-color: rgba(255, 137, 34, 0.6);
  background: rgba(255, 255, 255, 0.06);
  box-shadow: 0 0 0 4px rgba(255, 137, 34, 0.12);
}

.sms-code-row {
  display: flex;
  gap: 12px;
}

.sms-code-input {
  flex: 1;
}

.sms-send-btn {
  flex-shrink: 0;
  height: 52px;
  padding: 0 20px;
  border-radius: 14px;
  border: 1px solid var(--color-amber);
  background: rgba(255, 137, 34, 0.1);
  color: var(--color-amber);
  font-size: 13px;
  letter-spacing: 1px;
  white-space: nowrap;
  transition: all var(--duration-normal);
}

.sms-send-btn:hover:not(:disabled) {
  background: rgba(255, 137, 34, 0.18);
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(255, 137, 34, 0.15);
}

.sms-send-btn:disabled {
  opacity: 0.5;
}

.sms-dialog-btns {
  display: flex;
  gap: 12px;
  margin-top: 4px;
}

.sms-btn-cancel,
.sms-btn-confirm {
  flex: 1;
  height: 52px;
  border-radius: 14px;
  font-size: 15px;
  letter-spacing: 2px;
  transition: all var(--duration-normal);
}

.sms-btn-cancel {
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.03);
  color: var(--color-text-secondary);
}

.sms-btn-cancel:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.2);
}

.sms-btn-confirm {
  border: none;
  background: linear-gradient(135deg, #e67a1e, #cc6600);
  color: #fff;
  box-shadow: 0 6px 24px rgba(255, 137, 34, 0.35);
}

.sms-btn-confirm:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 32px rgba(255, 137, 34, 0.45);
}

.sms-btn-confirm:active:not(:disabled) {
  transform: translateY(0);
}

.footer-links {
  text-align: center;
}

.link-register {
  font-size: 14px;
  color: var(--color-text-dim);
  letter-spacing: 1px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 14px 24px;
  border-radius: 9999px;
  transition: all var(--duration-normal);
  background: rgba(255, 255, 255, 0);
}

.link-register:hover {
  color: var(--color-text-secondary);
  background: rgba(255, 255, 255, 0.04);
}

.link-register-text {
  color: var(--color-amber);
  font-weight: 500;
  position: relative;
}

.link-register-text::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 0;
  height: 1.5px;
  background: linear-gradient(90deg, var(--color-amber), rgba(255, 137, 34, 0.5));
  transition: width var(--duration-normal);
  box-shadow: 0 0 8px rgba(255, 137, 34, 0.4);
}

.link-register:hover .link-register-text::after {
  width: 100%;
}

.link-arrow {
  font-family: var(--font-mono);
  font-size: 12px;
  opacity: 0.8;
  transform: translateX(0);
  transition: transform var(--duration-normal), opacity var(--duration-normal);
}

.link-register:hover .link-arrow {
  transform: translateX(8px);
  opacity: 1;
}
</style>
