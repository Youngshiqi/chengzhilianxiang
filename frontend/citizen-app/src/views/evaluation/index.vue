<!--
  城市设施报修 · 市民端 — 服务评价
  霓虹混凝土：城市灯火 — 逐盏点亮星级 + 琥珀标签
-->
<template>
  <div class="eval-page">
    <!-- 顶部引导 -->
    <div class="eval-hero">
      <div class="hero-visual">
        <span class="hero-icon">⚡</span>
      </div>
      <p class="hero-text">
        工单 <span class="hero-id mono">{{ ticketId }}</span> 已完结
      </p>
      <p class="hero-sub">请评价本次维修服务</p>
    </div>

    <!-- 星级评分 — 城市灯火逐盏亮起 -->
    <div class="star-panel">
      <div class="star-lights">
        <button
          v-for="s in 5"
          :key="s"
          class="star-lamp"
          :class="{ lit: s <= form.star }"
          @click="form.star = s"
        >
          <span class="lamp-bulb">
            <span class="lamp-filament">✦</span>
          </span>
          <span class="lamp-base"></span>
        </button>
      </div>
      <div class="star-caption" v-if="form.star">
        <span class="caption-glow"></span>
        {{ starLabels[form.star] }}
      </div>
    </div>

    <!-- 快捷标签 -->
    <section class="tag-section">
      <header class="section-label">快捷标签（可多选）</header>
      <div class="tag-grid">
        <button
          v-for="t in quickTags"
          :key="t"
          class="tag-chip"
          :class="{ active: selectedTags.includes(t) }"
          @click="toggleTag(t)"
        >
          {{ t }}
        </button>
      </div>
    </section>

    <!-- 补充评价 -->
    <section class="comment-section">
      <header class="section-label">补充评价（可选）</header>
      <textarea
        v-model="form.comment"
        class="comment-input"
        placeholder="说说您的感受，帮助我们做得更好…"
        rows="4"
        maxlength="500"
      ></textarea>
      <span class="char-count mono">{{ form.comment.length }}/500</span>
    </section>

    <!-- 提交错误 -->
    <div v-if="evalError" class="eval-error">
      <span class="error-dot"></span> {{ evalError }}
    </div>

    <!-- 提交按钮 -->
    <button
      class="btn-submit"
      :class="{ active: form.star > 0 }"
      :disabled="!form.star || submitting"
      @click="handleSubmit"
    >
      <span v-if="submitting" class="btn-loading">
        <span class="load-ring"></span> 提交中
      </span>
      <span v-else>
        <span class="btn-star">★</span> 提交评价
      </span>
    </button>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { submitEvaluation } from '@/api/index'

const route = useRoute()
const router = useRouter()
const ticketId = route.params.id

const quickTags = [
  '响应迅速', '态度热情', '维修专业',
  '处理及时', '现场整洁', '技术过硬',
]
const starLabels = ['', '非常不满意', '不满意', '一般', '满意', '非常满意']

const form = reactive({ star: 0, comment: '', ticket_id: ticketId })
const selectedTags = ref([])
const submitting = ref(false)
const evalError = ref('')

function toggleTag(tag) {
  const idx = selectedTags.value.indexOf(tag)
  if (idx >= 0) selectedTags.value.splice(idx, 1)
  else selectedTags.value.push(tag)
}

async function handleSubmit() {
  if (!form.star || submitting.value) return
  evalError.value = ''
  submitting.value = true
  try {
    await submitEvaluation({
      ticket_id: ticketId,
      star: form.star,
      tags: selectedTags.value.join(','),
      comment: form.comment,
    })
    alert('评价提交成功，感谢您的反馈！')
    router.replace(`/ticket/${ticketId}`)
  } catch (e) {
    evalError.value = e.message || '评价提交失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.eval-page {
  padding: 0 16px 40px;
  max-width: 480px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ── Hero ── */
.eval-hero {
  text-align: center;
  padding: 16px 0 4px;
}
.hero-visual {
  width: 64px;
  height: 64px;
  margin: 0 auto 12px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(255, 137, 34, 0.15), rgba(255, 137, 34, 0.05));
  border: 1px solid rgba(255, 137, 34, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}
.hero-icon {
  font-size: 28px;
}
.hero-text {
  font-size: 16px;
  color: var(--color-text);
  margin-bottom: 2px;
}
.hero-id {
  font-size: 13px;
  color: var(--color-amber);
}
.hero-sub {
  font-size: 13px;
  color: var(--color-text-dim);
}

/* ── 城市灯火星级 ── */
.star-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: 24px 20px;
  text-align: center;
}

.star-lights {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.star-lamp {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  transition: transform var(--duration-fast) var(--ease-spring);
}
.star-lamp:active {
  transform: scale(0.9);
}

/* 灯泡 */
.lamp-bulb {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--color-bg-elevated);
  border: 2px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-normal) var(--ease-out-expo);
  position: relative;
}
.lamp-bulb::after {
  content: '';
  position: absolute;
  inset: -6px;
  border-radius: 50%;
  background: transparent;
  transition: all var(--duration-normal);
  z-index: -1;
}
.lamp-filament {
  font-size: 16px;
  color: var(--color-text-dim);
  transition: all var(--duration-normal);
}

.star-lamp.lit .lamp-bulb {
  background: rgba(255, 184, 0, 0.12);
  border-color: rgba(255, 184, 0, 0.5);
  box-shadow: 0 0 20px rgba(255, 184, 0, 0.25);
}
.star-lamp.lit .lamp-bulb::after {
  background: radial-gradient(circle, rgba(255, 184, 0, 0.2) 0%, transparent 70%);
}
.star-lamp.lit .lamp-filament {
  color: var(--color-yellow);
  text-shadow: 0 0 12px rgba(255, 184, 0, 0.6);
  animation: filament-glow 2s ease-in-out infinite;
}
@keyframes filament-glow {
  0%, 100% { text-shadow: 0 0 12px rgba(255, 184, 0, 0.6); }
  50% { text-shadow: 0 0 24px rgba(255, 184, 0, 0.9); }
}

/* 灯柱底座 */
.lamp-base {
  width: 4px;
  height: 8px;
  border-radius: 1px;
  background: var(--color-border);
  transition: background var(--duration-normal);
}
.star-lamp.lit .lamp-base {
  background: var(--color-yellow);
  box-shadow: 0 0 4px rgba(255, 184, 0, 0.4);
}

/* 评分文字 */
.star-caption {
  margin-top: 16px;
  font-size: 15px;
  font-weight: 600;
  color: var(--color-yellow);
  letter-spacing: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  animation: fade-up 0.3s var(--ease-out-expo);
}
.caption-glow {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-yellow);
  box-shadow: 0 0 8px var(--color-yellow);
}
@keyframes fade-up {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── 快捷标签 ── */
.tag-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 18px;
}
.section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  letter-spacing: 1px;
  margin-bottom: 12px;
  display: block;
}
.tag-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tag-chip {
  padding: 10px 18px;
  border-radius: var(--radius-full);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  font-size: 13px;
  color: var(--color-text-dim);
  transition: all var(--duration-fast) var(--ease-out-expo);
}
.tag-chip:active {
  transform: scale(0.95);
}
.tag-chip.active {
  background: var(--color-amber-dim);
  border-color: rgba(255, 137, 34, 0.35);
  color: var(--color-amber);
  box-shadow: 0 0 12px rgba(255, 137, 34, 0.1);
}

/* ── 补充评价 ── */
.comment-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 18px;
}
.comment-input {
  width: 100%;
  border: none;
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--color-text);
  background: var(--color-bg-elevated);
  resize: vertical;
  outline: none;
  border: 1px solid transparent;
  transition: border-color var(--duration-normal);
}
.comment-input:focus {
  border-color: var(--color-border-glow);
}
.comment-input::placeholder {
  color: var(--color-text-dim);
}
.char-count {
  font-size: 11px;
  color: var(--color-text-dim);
  display: block;
  text-align: right;
  margin-top: 6px;
}

/* ── 错误 ── */
.eval-error {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-red);
}
.error-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-red);
  box-shadow: 0 0 6px var(--color-red);
}

/* ── 提交 ── */
.btn-submit {
  width: 100%;
  height: 54px;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text-dim);
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  transition: all var(--duration-normal) var(--ease-out-expo);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.btn-submit.active {
  background: linear-gradient(135deg, #e67a1e, #cc6000);
  border-color: transparent;
  color: #fff;
  box-shadow: var(--shadow-glow-amber);
}
.btn-submit.active:active {
  transform: scale(0.97);
}
.btn-submit:disabled {
  cursor: not-allowed;
}
.btn-star {
  font-size: 18px;
}

.btn-loading {
  display: flex;
  align-items: center;
  gap: 10px;
}
.load-ring {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255,255,255,0.25);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
