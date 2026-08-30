<!--
  城市设施运维指挥中心 — 登录页
  暗色指挥舱风格登录卡片
-->
<template>
  <div class="login-shell">
    <div class="login-card">
      <div class="login-header">
        <div class="brand-icon">▦</div>
        <h1 class="brand-name">CityRepair</h1>
        <p class="brand-desc">城市设施运维指挥中心</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" class="login-form" @submit.prevent="handleLogin">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
            :prefix-icon="Lock"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          class="login-btn"
          :loading="loading"
          @click="handleLogin"
        >
          登 录
        </el-button>
      </el-form>
      <div class="login-footer mono">
        <span>v3.0 · JWT Auth</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login } from '@/api/index'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少6位', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await login(form.username, form.password)
    localStorage.setItem('admin_token', res.data.token)
    localStorage.setItem('admin_user', JSON.stringify(res.data))
    ElMessage.success('登录成功')
    router.replace('/dashboard')
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-shell {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--bg-base);
}

.login-card {
  width: 400px;
  padding: 48px 40px 32px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-dim);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-elevated);
}

.login-header {
  text-align: center;
  margin-bottom: 36px;
}

.brand-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 14px;
  background: linear-gradient(135deg, var(--signal-amber), #cc5500);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: #fff;
}

.brand-name {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 3px;
  color: var(--text-primary);
  margin: 0;
}

.brand-desc {
  font-size: 12px;
  color: var(--text-muted);
  letter-spacing: 2px;
  margin: 6px 0 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.login-btn {
  width: 100%;
  margin-top: 8px;
  font-family: var(--font-mono);
  letter-spacing: 4px;
}

.login-footer {
  text-align: center;
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 1px;
  margin-top: 24px;
}
</style>
