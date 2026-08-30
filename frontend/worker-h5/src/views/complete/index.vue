<!--
  城市设施报修 · 维修工端 — 完工闭环
  重工仪表：工业表单 + 钢质输入框 + 终端绿提交
-->
<template>
  <div class="complete-page">
    <!-- 顶栏 -->
    <header class="nav-bar">
      <button class="btn-back" @click="$router.back()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>
      <span class="nav-title">完工闭环</span>
      <span class="nav-spacer"></span>
    </header>

    <!-- 表单卡片 -->
    <div class="form-card">
      <!-- 铆钉四角 -->
      <span class="rivet r1"></span>
      <span class="rivet r2"></span>
      <span class="rivet r3"></span>
      <span class="rivet r4"></span>

      <!-- 完工拍照 -->
      <section class="section">
        <h3 class="section-label">
          完工拍照
          <span class="label-hint">（选填，最多 5 张）</span>
        </h3>
        <div class="photo-area">
          <!-- 已选照片缩略图 -->
          <div
            v-for="(item, i) in photoItems"
            :key="i"
            class="photo-thumb"
            :class="{ uploading: item.uploading, error: item.error }"
          >
            <!-- 预览图 -->
            <img v-if="item.preview" :src="item.preview" class="photo-preview" alt="" />
            <span v-else class="photo-icon">📷</span>

            <!-- 上传进度遮罩 -->
            <div v-if="item.uploading" class="photo-overlay">
              <div class="progress-ring">
                <span class="progress-text">{{ item.progress }}%</span>
              </div>
            </div>

            <!-- 上传失败遮罩 -->
            <div v-if="item.error" class="photo-overlay error-overlay">
              <button class="btn-retry" @click.stop="retryUpload(i)">重试</button>
            </div>

            <!-- 删除按钮 -->
            <button
              v-if="!item.uploading"
              class="photo-remove"
              @click="removePhoto(i)"
            >✕</button>
          </div>

          <!-- 添加按钮 -->
          <button
            class="btn-add-photo"
            @click="triggerFileInput"
            v-if="photoItems.length < 5"
          >
            <span class="add-icon">+</span>
          </button>
        </div>

        <!-- 隐藏的文件选择 -->
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          capture="environment"
          style="display: none"
          @change="onFileSelected"
        />

        <p class="photo-hint">拍摄维修后的设施照片，用于 AI 验收比对</p>
      </section>

      <!-- 耗材录入 -->
      <section class="section">
        <h3 class="section-label">
          耗材使用
          <span class="label-hint" v-if="totalMaterialCost > 0">（合计：¥{{ totalMaterialCost.toFixed(2) }}）</span>
        </h3>

        <!-- 表头说明 -->
        <div class="material-header">
          <span class="header-label name">耗材名称</span>
          <span class="header-label qty">数量</span>
          <span class="header-label cost">单价（元）</span>
          <span class="header-label total">小计（元）</span>
        </div>

        <!-- 耗材行 -->
        <div v-for="(m, i) in materials" :key="i" class="material-card">
          <div class="material-main">
            <div class="field-group name-field">
              <label class="field-label">名称</label>
              <input v-model="m.name" placeholder="如：LED灯泡、绝缘胶带" class="input-name" />
            </div>
            <div class="field-row">
              <div class="field-group">
                <label class="field-label">数量</label>
                <input v-model.number="m.qty" placeholder="0" type="number" min="0" class="input-qty" />
              </div>
              <div class="field-group">
                <label class="field-label">单价</label>
                <input v-model.number="m.unit_cost" placeholder="0.00" type="number" min="0" step="0.01" class="input-cost" />
              </div>
              <div class="field-group subtotal-group">
                <label class="field-label">小计</label>
                <div class="subtotal-value">¥{{ (m.qty * m.unit_cost).toFixed(2) }}</div>
              </div>
            </div>
          </div>
          <button class="btn-remove-material" @click="materials.splice(i, 1)" title="删除此耗材">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <button class="btn-add-material" @click="materials.push({ name: '', qty: 0, unit_cost: 0 })">
          <span class="btn-icon">+</span>
          <span>添加耗材</span>
        </button>
      </section>

      <!-- 工时 -->
      <section class="section">
        <h3 class="section-label">维修工时（小时）</h3>
        <input
          v-model.number="laborHours"
          type="number"
          step="0.5"
          min="0"
          placeholder="例如：1.5"
          class="input-full"
        />
      </section>

      <!-- 备注 -->
      <section class="section">
        <h3 class="section-label">
          维修备注
          <span class="label-hint">（选填）</span>
        </h3>
        <textarea
          v-model="notes"
          class="textarea"
          placeholder="记录维修过程中的特殊情况..."
          rows="3"
          maxlength="300"
        ></textarea>
        <span class="char-count mono">{{ notes.length }}/300</span>
      </section>

      <!-- 错误提示 -->
      <div v-if="errorMsg" class="error-msg">
        <span class="error-dot"></span> {{ errorMsg }}
      </div>

      <!-- 提交按钮 -->
      <button
        class="btn-submit"
        :disabled="!canSubmit || submitting || hasUploading"
        @click="handleSubmit"
      >
        <span v-if="submitting" class="btn-spinner"></span>
        <span v-else>✅ 提交完工</span>
      </button>

      <!-- AI 验收结果 -->
      <div v-if="aiResult" class="ai-result">
        <div class="ai-header">
          <span class="ai-icon">🤖</span>
          <span class="ai-title">AI 验收结果</span>
        </div>
        <div class="ai-body">
          <div class="ai-row">
            <span class="ai-label">验收状态</span>
            <span class="ai-value" :class="aiResult.ai_verified ? 'pass' : 'warn'">
              {{ aiResult.ai_verified ? '✅ 通过' : '⚠️ 待审核' }}
            </span>
          </div>
          <div v-if="aiResult.ai_confidence != null" class="ai-row">
            <span class="ai-label">置信度</span>
            <span class="ai-value mono">{{ (aiResult.ai_confidence * 100).toFixed(0) }}%</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { completeTicket } from '@/api/index'
import { uploadImage } from '@/utils/upload'

const route = useRoute()
const router = useRouter()
const ticketId = route.params.id

// 照片列表：{ preview, url, uploading, progress, error, _file }
const photoItems = ref([])
const fileInput = ref(null)
const materials = ref([{ name: '', qty: 0, unit_cost: 0 }])
const laborHours = ref(0)
const notes = ref('')
const submitting = ref(false)
const errorMsg = ref('')
const aiResult = ref(null)

const canSubmit = computed(() => laborHours.value > 0)
const hasUploading = computed(() => photoItems.value.some(p => p.uploading))
const totalMaterialCost = computed(() => {
  return materials.value.reduce((sum, m) => sum + (m.qty * m.unit_cost), 0)
})

/** 已成功上传的 OSS URL 列表 */
function uploadedUrls() {
  return photoItems.value
    .filter(p => p.url && !p.error)
    .map(p => p.url)
}

function triggerFileInput() {
  fileInput.value?.click()
}

function onFileSelected(e) {
  const files = e.target.files
  if (!files || !files.length) return

  for (const file of files) {
    if (photoItems.value.length >= 5) break
    uploadSingle(file)
  }

  // 重置 input，允许重复选择同一文件
  e.target.value = ''
}

/** 更新照片列表中的某一项（触发 Vue 3 ref 响应式） */
function setPhotoItem(i, patch) {
  photoItems.value[i] = { ...photoItems.value[i], ...patch }
}

async function uploadSingle(file) {
  const i = photoItems.value.length
  const preview = URL.createObjectURL(file)
  photoItems.value.push({ preview, url: '', uploading: true, progress: 0, error: false, _file: file })

  try {
    const url = await uploadImage(file, (percent) => {
      setPhotoItem(i, { progress: percent })
    })
    setPhotoItem(i, { url, uploading: false, progress: 100 })
  } catch (e) {
    setPhotoItem(i, { error: true, uploading: false })
    errorMsg.value = e.message || '图片上传失败'
    setTimeout(() => { errorMsg.value = '' }, 3000)
  }
}

function retryUpload(i) {
  const item = photoItems.value[i]
  if (!item._file) return
  setPhotoItem(i, { error: false, uploading: true, progress: 0 })

  uploadImage(item._file, (percent) => {
    setPhotoItem(i, { progress: percent })
  })
    .then((url) => {
      setPhotoItem(i, { url, uploading: false, progress: 100 })
    })
    .catch((e) => {
      setPhotoItem(i, { error: true, uploading: false })
      errorMsg.value = e.message || '重试上传失败'
      setTimeout(() => { errorMsg.value = '' }, 3000)
    })
}

function removePhoto(i) {
  const item = photoItems.value[i]
  if (item.preview && item.preview.startsWith('blob:')) {
    URL.revokeObjectURL(item.preview)
  }
  photoItems.value.splice(i, 1)
}

async function handleSubmit() {
  if (!canSubmit.value || submitting.value || hasUploading.value) return
  errorMsg.value = ''
  aiResult.value = null
  submitting.value = true
  try {
    const data = await completeTicket(ticketId, {
      materials: materials.value.filter(m => m.name && m.qty > 0),
      labor_hours: laborHours.value,
      work_notes: notes.value,
      completion_photo_urls: uploadedUrls(),
    })
    aiResult.value = data || null
    if (!aiResult.value || aiResult.value.ai_verified) {
      setTimeout(() => {
        router.replace(`/ticket/${ticketId}`)
      }, 2000)
    }
  } catch (e) {
    errorMsg.value = e.message || '提交失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.complete-page {
  padding: 0 16px 24px;
  max-width: 480px;
  margin: 0 auto;
}

/* ── 顶栏 ── */
.nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 0 14px;
}
.btn-back {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  transition: border-color var(--duration-fast);
}
.btn-back:active { border-color: var(--color-primary); }
.nav-title { font-size: 15px; font-weight: 600; }
.nav-spacer { width: 36px; }

/* ── 表单卡片 ── */
.form-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 22px 18px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: relative;
}

/* 铆钉 */
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

/* ── 分区 ── */
.section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  letter-spacing: 0.5px;
}
.label-hint {
  font-weight: 400;
  color: var(--color-text-dim);
  font-size: 12px;
}

/* ── 拍照 ── */
.photo-area {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.photo-thumb {
  width: 68px;
  height: 68px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-raised);
  border: 1px dashed var(--color-border-active);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}
.photo-thumb.uploading {
  border-color: var(--color-primary);
}
.photo-thumb.error {
  border-color: var(--color-danger);
}
.photo-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.photo-icon {
  font-size: 24px;
  opacity: 0.4;
}
.photo-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
}
.progress-ring {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: var(--color-primary);
  animation: spin 0.8s linear infinite;
  display: flex;
  align-items: center;
  justify-content: center;
}
.progress-text {
  font-size: 9px;
  color: #fff;
  animation: spin-reverse 0.8s linear infinite;
}
.error-overlay {
  background: rgba(211, 47, 47, 0.5);
}
.btn-retry {
  font-size: 11px;
  color: #fff;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 4px;
  padding: 2px 8px;
}
.photo-remove {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-danger);
  color: #fff;
  font-size: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.btn-add-photo {
  width: 68px;
  height: 68px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-raised);
  border: 1px dashed var(--color-border-active);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color var(--duration-fast);
}
.btn-add-photo:active {
  border-color: var(--color-primary);
}
.add-icon {
  font-size: 28px;
  color: var(--color-text-dim);
}
.photo-hint {
  font-size: 11px;
  color: var(--color-text-dim);
}

/* ── 耗材 ── */
.material-header {
  display: grid;
  grid-template-columns: 1.5fr 0.8fr 0.8fr 0.8fr;
  gap: 6px;
  padding: 0 2px 8px;
  border-bottom: 2px solid var(--color-border);
  margin-bottom: 12px;
}
.header-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--color-text-dim);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  white-space: nowrap;
}
.header-label.name { grid-column: 1; }
.header-label.qty { grid-column: 2; text-align: center; }
.header-label.cost { grid-column: 3; text-align: center; }
.header-label.total { grid-column: 4; text-align: right; }

.material-card {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 10px;
  margin-bottom: 10px;
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast);
  box-sizing: border-box;
  width: 100%;
}
.material-card:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(255, 107, 0, 0.1);
}
.material-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  width: 100%;
}
.field-group {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.name-field { flex: 1; }
.field-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.2px;
}
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 6px;
}
.input-name, .input-qty, .input-cost {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-size: 13px;
  background: var(--color-bg);
  color: var(--color-text);
  outline: none;
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast);
  width: 100%;
  box-sizing: border-box;
}
.input-name:focus, .input-qty:focus, .input-cost:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(255, 107, 0, 0.1);
}
.input-name::placeholder { color: var(--color-text-dim); font-size: 12px; }
.input-qty, .input-cost {
  text-align: center;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
}
.subtotal-group {
  justify-content: flex-end;
}
.subtotal-value {
  padding: 8px 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
  text-align: right;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
  background: rgba(255, 107, 0, 0.08);
  border-radius: var(--radius-sm);
  white-space: nowrap;
}
.btn-remove-material {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--color-danger-dim);
  border: 1px solid var(--color-danger-dim);
  color: var(--color-danger);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--duration-fast);
  margin-top: 18px;
}
.btn-remove-material:hover, .btn-remove-material:active {
  background: var(--color-danger);
  color: #fff;
}
.btn-add-material {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 14px;
  color: var(--color-primary);
  background: var(--color-primary-dim);
  border: 1px dashed var(--color-primary);
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-weight: 500;
  align-self: stretch;
  transition: all var(--duration-fast);
  width: 100%;
  box-sizing: border-box;
}
.btn-add-material:active {
  background: rgba(255, 107, 0, 0.2);
  transform: scale(0.98);
}
.btn-icon {
  font-size: 20px;
  font-weight: 600;
  line-height: 1;
}

/* ── 工时输入 ── */
.input-full {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  font-size: 15px;
  background: var(--color-bg-elevated);
  color: var(--color-text);
  outline: none;
  transition: border-color var(--duration-fast);
}
.input-full:focus {
  border-color: var(--color-primary);
}
.input-full::placeholder {
  color: var(--color-text-dim);
}

/* ── 备注 ── */
.textarea {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--color-text);
  background: var(--color-bg-elevated);
  resize: vertical;
  outline: none;
  transition: border-color var(--duration-fast);
}
.textarea:focus {
  border-color: var(--color-primary);
}
.textarea::placeholder {
  color: var(--color-text-dim);
}
.char-count {
  font-size: 11px;
  color: var(--color-text-dim);
  text-align: right;
}

/* ── 错误 ── */
.error-msg {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-danger);
}
.error-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-danger);
  box-shadow: 0 0 6px var(--color-danger);
}

/* ── 提交按钮 ── */
.btn-submit {
  width: 100%;
  height: 50px;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, #00C853, #009624);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 1px;
  box-shadow: 0 2px 14px rgba(0, 230, 118, 0.25);
  transition: transform var(--duration-fast);
  display: flex;
  align-items: center;
  justify-content: center;
}
.btn-submit:active:not(:disabled) {
  transform: scale(0.97);
}
.btn-submit:disabled {
  opacity: 0.45;
}

.btn-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255,255,255,0.25);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes spin-reverse { to { transform: rotate(-360deg); } }

/* ── AI 验收结果 ── */
.ai-result {
  background: var(--color-success-dim);
  border: 1px solid rgba(0, 230, 118, 0.2);
  border-radius: var(--radius-md);
  padding: 16px;
}
.ai-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.ai-icon { font-size: 18px; }
.ai-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-success);
}
.ai-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ai-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}
.ai-label {
  color: var(--color-text-dim);
}
.ai-value {
  color: var(--color-text);
  font-weight: 500;
}
.ai-value.pass { color: var(--color-success); }
.ai-value.warn { color: var(--color-warning); }
</style>
