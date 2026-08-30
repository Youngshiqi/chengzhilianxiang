<!--
  城市设施报修 · 市民端 — 报修首页
  霓虹混凝土：市政控制面板 — 设施选择面板 + 琥珀提交
-->
<template>
  <div class="home-page">
    <!-- Hero 横幅 -->
    <section class="hero">
      <div class="hero-glow"></div>
      <h2 class="hero-title">报告设施故障</h2>
      <p class="hero-sub">选择故障类型，描述现场情况。维修力量将迅速响应。</p>
    </section>

    <!-- 设施类型面板 -->
    <section class="panel">
      <header class="panel-header">
        <span class="panel-dot"></span>
        <span class="panel-label mono">设施类型</span>
        <span class="panel-hint">选择一项</span>
      </header>
      <div class="type-grid">
        <button
          v-for="t in facilityTypes"
          :key="t"
          class="type-chip"
          :class="{ active: form.facility_type === t }"
          @click="form.facility_type = t"
        >
          <span class="type-icon">{{ getFacilityIcon(t) }}</span>
          <span class="type-name">{{ t }}</span>
        </button>
      </div>
    </section>

    <!-- 故障描述 -->
    <section class="panel">
      <header class="panel-header">
        <span class="panel-dot"></span>
        <span class="panel-label mono">故障描述</span>
        <span class="panel-hint mono">{{ form.description.length }}/500</span>
      </header>
      <textarea
        v-model="form.description"
        class="desc-input"
        placeholder="请详细描述故障情况，帮助维修员快速定位问题…

例如：人民路与建设路交叉口西北角路灯不亮，灯杆编号 LD-2024-0188，已持续 3 天。"
        rows="5"
        maxlength="500"
      ></textarea>
    </section>

    <!-- 位置 -->
    <section class="panel">
      <header class="panel-header">
        <span class="panel-dot"></span>
        <span class="panel-label mono">故障位置</span>
        <span v-if="form.location_lat" class="panel-badge live">已定位</span>
      </header>
      <div class="location-box" @click="openMapPicker">
        <div class="loc-indicator" :class="{ active: form.location_lat }">
          <span class="loc-ring"></span>
          <span class="loc-dot"></span>
        </div>
        <div class="loc-info">
          <span v-if="form.address" class="loc-text">{{ form.address }}</span>
          <span v-else class="loc-placeholder">点击选择故障位置</span>
        </div>
        <span class="loc-action mono">{{ locating ? '…' : '选点' }}</span>
      </div>
      <div v-if="locError" class="loc-error">
        <span class="error-dot"></span> {{ locError }}
      </div>
    </section>

    <!-- 紧急程度 -->
    <section class="panel">
      <header class="panel-header">
        <span class="panel-dot"></span>
        <span class="panel-label mono">紧急程度</span>
      </header>
      <div class="urgency-row">
        <button
          class="urgency-chip"
          :class="{ active: form.emergency_level === 0 }"
          @click="form.emergency_level = 0"
        >
          <span class="urgency-indicator normal">
            <span class="urg-ring"></span>
          </span>
          <span class="urg-label">普通报修</span>
          <span class="urg-desc">常规响应时效</span>
        </button>
        <button
          class="urgency-chip emergency-chip"
          :class="{ active: form.emergency_level === 1 }"
          @click="form.emergency_level = 1"
        >
          <span class="urgency-indicator emergency">
            <span class="urg-ring"></span>
          </span>
          <span class="urg-label">紧急报修</span>
          <span class="urg-desc">优先加速处理</span>
        </button>
      </div>
    </section>

    <!-- 照片上传 -->
    <section class="panel">
      <header class="panel-header">
        <span class="panel-dot" :class="{ dim: form.image_urls.length === 0 }"></span>
        <span class="panel-label mono">现场照片</span>
        <span class="panel-hint">{{ form.image_urls.length }}/5</span>
      </header>
      <!-- 隐藏的文件选择器 -->
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        capture="environment"
        style="display:none"
        @change="onFileSelected"
      />
      <div class="photo-area">
        <!-- 已上传/上传中的缩略图 -->
        <div
          v-for="(item, i) in photoItems"
          :key="i"
          class="photo-thumb"
          :class="{ uploading: item.uploading, error: item.error }"
        >
          <img v-if="item.preview" :src="item.preview" class="thumb-img" />
          <span v-else class="thumb-placeholder">📷</span>
          <!-- 上传进度遮罩 -->
          <div v-if="item.uploading" class="upload-overlay">
            <span class="upload-percent">{{ item.progress }}%</span>
          </div>
          <!-- 上传失败遮罩 -->
          <div v-if="item.error" class="error-overlay" @click.stop="retryUpload(i)">
            <span class="error-icon">!</span>
          </div>
          <!-- 删除按钮 -->
          <button
            v-if="!item.uploading"
            class="delete-btn"
            @click.stop="removePhoto(i)"
          >✕</button>
        </div>
        <!-- 添加按钮 -->
        <button
          v-if="form.image_urls.length < 5"
          class="btn-add-photo"
          @click="triggerFileInput"
          :disabled="uploadingCount > 0 && uploadingCount >= 2"
        >
          <span class="add-icon">+</span>
        </button>
      </div>
      <div v-if="uploadError" class="upload-error">
        <span class="error-dot"></span> {{ uploadError }}
      </div>
    </section>

    <!-- 错误提示 -->
    <div v-if="submitError" class="submit-error">
      <span class="error-dot"></span> {{ submitError }}
    </div>

    <!-- 提交按钮 -->
    <div class="submit-area">
      <button
        class="btn-submit"
        :class="{ ready: canSubmit }"
        :disabled="!canSubmit || submitting || uploadingCount > 0"
        @click="handleSubmit"
      >
        <span v-if="submitting" class="btn-loading">
          <span class="pulse-ring"></span>
          提交中…
        </span>
        <span v-else-if="uploadingCount > 0" class="btn-ready">
          <span class="submit-icon">⏳</span>
          图片上传中 ({{ uploadingCount }})
        </span>
        <span v-else class="btn-ready">
          <span class="submit-icon">⚡</span>
          提交报修
        </span>
      </button>
      <!-- 未就绪提示 — 琥珀色醒目卡片 -->
      <div v-if="!canSubmit" class="submit-hint">
        <div class="hint-card">
          <div class="hint-header">
            <span class="hint-icon">⚡</span>
            <span class="hint-title">你还需要</span>
          </div>
          <div class="hint-items">
            <div v-if="!form.facility_type" class="hint-item">
              <span class="hint-bullet"></span>
              <span>选择故障设施类型</span>
            </div>
            <div v-if="form.description.length < 10" class="hint-item">
              <span class="hint-bullet"></span>
              <span>描述至少 10 个字（还差 {{ 10 - form.description.length }} 字）</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 最近工单 -->
    <section v-if="recentTickets.length" class="recent-section">
      <header class="section-header">
        <span class="section-title">最近工单</span>
        <router-link to="/my-tickets" class="link-all mono">
          全部 <span class="link-arrow">→</span>
        </router-link>
      </header>
      <div class="recent-list">
        <router-link
          v-for="t in recentTickets"
          :key="t.ticket_id"
          :to="`/ticket/${t.ticket_id}`"
          class="recent-card"
        >
          <div class="rc-left">
            <span class="rc-type">{{ getFacilityIcon(t.facility_type) }}</span>
            <div class="rc-info">
              <div class="rc-desc">{{ (t.description || '').slice(0, 28) }}</div>
              <div class="rc-time mono">{{ formatTime(t.created_at) }}</div>
            </div>
          </div>
          <span class="rc-status" :class="'st-' + t.status">
            {{ STATUS_MAP[t.status]?.label || t.status }}
          </span>
        </router-link>
      </div>
    </section>

    <!-- 地图选点弹窗 -->
    <Teleport to="body">
      <div v-if="showMapPicker" class="map-overlay">
        <div class="map-modal">
          <!-- 顶栏 -->
          <div class="map-topbar">
            <button class="map-btn-cancel" @click="closeMapPicker">取消</button>
            <span class="map-title mono">拖动地图选择位置</span>
            <button
              class="map-btn-confirm"
              :class="{ active: !mapPicking }"
              :disabled="mapPicking"
              @click="confirmMapPick"
            >
              {{ mapPicking ? '解析中…' : '确认' }}
            </button>
          </div>
          <!-- 地图容器 -->
          <div id="map-picker-container" class="map-container"></div>
          <!-- 十字准星提示 -->
          <div class="map-crosshair-hint">
            <span class="crosshair-dot"></span>
            <span>将目标位置对准十字中心，点击"确认"</span>
          </div>
          <!-- 底部 GPS 快捷按钮 -->
          <div class="map-gps-bar">
            <button class="map-btn-gps" @click="quickGpsLocate">
              <span class="gps-icon">◎</span>
              <span>定位到我的位置</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 成功弹窗 -->
    <Teleport to="body">
      <div v-if="showSuccess" class="overlay" @click.self="showSuccess = false">
        <div class="success-card">
          <div class="success-ring">
            <span class="success-icon">✓</span>
          </div>
          <h3 class="success-title">报修已受理</h3>
          <div class="success-id mono">{{ lastTicketId }}</div>
          <p v-if="lastAiCategory" class="success-ai">AI 识别：{{ lastAiCategory }}</p>
          <div class="success-actions">
            <button class="btn-secondary" @click="showSuccess = false">继续报修</button>
            <router-link :to="`/ticket/${lastTicketId}`" class="btn-primary">查看进度 →</router-link>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { createTicket, getMyTickets } from '@/api/index'
import { getFacilityIcon, STATUS_MAP, formatTime } from '@/utils'
import { uploadImage } from '@/utils/upload'

const router = useRouter()

const DRAFT_KEY = 'report_draft_image_urls'

function saveDraft() {
  try {
    if (form.image_urls.length > 0) {
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify(form.image_urls))
    }
  } catch {}
}

function loadDraft() {
  try {
    const raw = sessionStorage.getItem(DRAFT_KEY)
    if (raw) {
      const urls = JSON.parse(raw)
      if (Array.isArray(urls) && urls.length > 0) {
        form.image_urls = urls.filter(u => typeof u === 'string' && u.startsWith('http'))
      }
    }
  } catch {}
}

function clearDraft() {
  try { sessionStorage.removeItem(DRAFT_KEY) } catch {}
}

const facilityTypes = [
  '路灯', '井盖', '护栏', '信号灯', '公交站牌',
  '消防栓', '公厕', '指示牌', '垃圾桶', '健身器材', '其他',
]

const form = reactive({
  facility_type: '',
  description: '',
  location_lng: 0,
  location_lat: 0,
  address: '',
  image_urls: [],
  emergency_level: 0,
})

const locating = ref(false)
const locError = ref('')
const submitting = ref(false)
const submitError = ref('')
const showSuccess = ref(false)
const lastTicketId = ref('')
const lastAiCategory = ref('')
const recentTickets = ref([])

// ---------- 地图选点 ----------
const showMapPicker = ref(false)
const mapInstance = ref(null)
const mapMarker = ref(null)
const mapGeocoder = ref(null)
const mapCenter = ref([112.9388, 28.2282])
const mapPickedLocation = ref({ lng: 0, lat: 0, address: '' })
const mapPicking = ref(false)

const canSubmit = computed(() =>
  form.facility_type && form.description.length >= 10
)

function getLocation() {
  if (!navigator.geolocation) {
    locError.value = '浏览器不支持定位，已使用默认位置'
    setDefaultLocation()
    return
  }
  locating.value = true
  locError.value = ''
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      form.location_lng = pos.coords.longitude
      form.location_lat = pos.coords.latitude
      applyReverseGeocode(pos.coords.longitude, pos.coords.latitude)
    },
    () => {
      locError.value = 'GPS 定位失败，已使用默认位置'
      locating.value = false
      setDefaultLocation()
    },
    { enableHighAccuracy: true, timeout: 10000 },
  )
}

function applyReverseGeocode(lng, lat) {
  if (window.AMap) {
    AMap.plugin('AMap.Geocoder', () => {
      const geocoder = new AMap.Geocoder()
      geocoder.getAddress([lng, lat], (status, result) => {
        if (status === 'complete' && result.regeocode) {
          form.address = result.regeocode.formattedAddress || `${lng.toFixed(6)}, ${lat.toFixed(6)}`
        } else {
          form.address = `${lng.toFixed(6)}, ${lat.toFixed(6)}`
        }
        form.location_lng = lng
        form.location_lat = lat
        locating.value = false
      })
    })
  } else {
    form.address = `${lng.toFixed(6)}, ${lat.toFixed(6)}`
    form.location_lng = lng
    form.location_lat = lat
    locating.value = false
  }
}

function setDefaultLocation() {
  form.location_lng = 112.9388
  form.location_lat = 28.2282
  form.address = '长沙市芙蓉区（默认位置）'
}

// ---------- 地图选点 ----------
async function openMapPicker() {
  showMapPicker.value = true
  mapPicking.value = false
  mapPickedLocation.value = { lng: 0, lat: 0, address: '' }
  // 用当前已有坐标或默认坐标
  const lng = form.location_lng || 112.9388
  const lat = form.location_lat || 28.2282
  mapCenter.value = [lng, lat]

  await nextTick()
  initMap()
}

function initMap() {
  if (!window.AMap) {
    locError.value = '地图服务不可用，请使用 GPS 定位'
    showMapPicker.value = false
    return
  }
  // 销毁旧实例
  if (mapInstance.value) {
    mapInstance.value.destroy()
    mapInstance.value = null
  }

  const [lng, lat] = mapCenter.value
  mapInstance.value = new AMap.Map('map-picker-container', {
    zoom: 16,
    center: [lng, lat],
    resizeEnable: true,
  })

  // 中心十字标记
  mapMarker.value = new AMap.Marker({
    position: [lng, lat],
    offset: new AMap.Pixel(-12, -36),
    content: '<div style="width:24px;height:36px;display:flex;align-items:center;justify-content:center;"><svg viewBox="0 0 24 36" width="24" height="36"><path d="M12 0C5.4 0 0 5.4 0 12c0 9 12 24 12 24s12-15 12-24c0-6.6-5.4-12-12-12zm0 16.5a4.5 4.5 0 1 1 0-9 4.5 4.5 0 0 1 0 9z" fill="#ff8922" stroke="#fff" stroke-width="1.5"/></svg></div>',
  })
  mapMarker.value.setMap(mapInstance.value)

  // 逆地理编码器
  AMap.plugin('AMap.Geocoder', () => {
    mapGeocoder.value = new AMap.Geocoder()
  })

  // 地图移动时更新标记位置
  mapInstance.value.on('moveend', () => {
    const center = mapInstance.value.getCenter()
    if (center && mapMarker.value) {
      mapMarker.value.setPosition([center.lng, center.lat])
    }
  })
}

function confirmMapPick() {
  if (!mapInstance.value) return
  const center = mapInstance.value.getCenter()
  if (!center) return
  const lng = center.lng
  const lat = center.lat
  mapPickedLocation.value = { lng, lat, address: '' }
  mapPicking.value = true

  if (mapGeocoder.value) {
    mapGeocoder.value.getAddress([lng, lat], (status, result) => {
      if (status === 'complete' && result.regeocode) {
        mapPickedLocation.value.address = result.regeocode.formattedAddress || `${lng.toFixed(6)}, ${lat.toFixed(6)}`
      } else {
        mapPickedLocation.value.address = `${lng.toFixed(6)}, ${lat.toFixed(6)}`
      }
      applyMapPick()
    })
  } else if (window.AMap) {
    AMap.plugin('AMap.Geocoder', () => {
      const gc = new AMap.Geocoder()
      gc.getAddress([lng, lat], (status, result) => {
        if (status === 'complete' && result.regeocode) {
          mapPickedLocation.value.address = result.regeocode.formattedAddress || `${lng.toFixed(6)}, ${lat.toFixed(6)}`
        } else {
          mapPickedLocation.value.address = `${lng.toFixed(6)}, ${lat.toFixed(6)}`
        }
        applyMapPick()
      })
    })
  } else {
    mapPickedLocation.value.address = `${lng.toFixed(6)}, ${lat.toFixed(6)}`
    applyMapPick()
  }
}

function applyMapPick() {
  const { lng, lat, address } = mapPickedLocation.value
  form.location_lng = lng
  form.location_lat = lat
  form.address = address
  locError.value = ''
  mapPicking.value = false
  showMapPicker.value = false
  destroyMap()
}

function closeMapPicker() {
  showMapPicker.value = false
  destroyMap()
}

function destroyMap() {
  if (mapInstance.value) {
    mapInstance.value.destroy()
    mapInstance.value = null
  }
  mapMarker.value = null
  mapGeocoder.value = null
}

function quickGpsLocate() {
  if (!navigator.geolocation) return
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const { longitude, latitude } = pos.coords
      mapCenter.value = [longitude, latitude]
      if (mapInstance.value) {
        mapInstance.value.setCenter([longitude, latitude])
      }
    },
    () => {},
    { enableHighAccuracy: true, timeout: 8000 },
  )
}

// 页面加载时自动获取位置
onMounted(() => {
  loadDraft()
  setDefaultLocation()  // 先设默认值，确保表单始终可提交
  getLocation()          // 再尝试精确定位
  loadRecentTickets()
})

onUnmounted(() => {
  destroyMap()
})

// ---------- 图片上传 ----------
const fileInput = ref(null)
// 上传中间态：{ preview, url, uploading, progress, error }
const photoItems = ref([])
const uploadingCount = ref(0)
const uploadError = ref('')

function triggerFileInput() {
  fileInput.value?.click()
}

async function onFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return

  // 重置 input 以便重复选择同一文件
  e.target.value = ''

  const idx = photoItems.value.length
  const preview = URL.createObjectURL(file)

  // 添加占位项（上传中）
  photoItems.value.push({ preview, url: '', uploading: true, progress: 0, error: false })
  uploadingCount.value++

  try {
    const ossUrl = await uploadImage(file, (percent) => {
      if (photoItems.value[idx]) {
        photoItems.value[idx].progress = percent
      }
    })
    // 上传成功：写入 OSS URL
    photoItems.value[idx] = { preview, url: ossUrl, uploading: false, progress: 100, error: false }
    form.image_urls.push(ossUrl)
    saveDraft()
    uploadError.value = ''
  } catch (e) {
    // 上传失败：显示重试
    photoItems.value[idx] = { preview, url: '', uploading: false, progress: 0, error: true, _file: file }
    uploadError.value = e.message || '图片上传失败'
  } finally {
    uploadingCount.value--
  }
}

function removePhoto(i) {
  const item = photoItems.value[i]
  if (item.url) {
    const urlIdx = form.image_urls.indexOf(item.url)
    if (urlIdx !== -1) form.image_urls.splice(urlIdx, 1)
    saveDraft()
  }
  if (item.preview) URL.revokeObjectURL(item.preview)
  photoItems.value.splice(i, 1)
}

function retryUpload(i) {
  const item = photoItems.value[i]
  if (!item._file) return
  // 移除失败项
  if (item.preview) URL.revokeObjectURL(item.preview)
  photoItems.value.splice(i, 1)
  // 重新上传
  const dt = new DataTransfer()
  dt.items.add(item._file)
  onFileSelected({ target: { files: dt.files, value: '' } })
}

async function handleSubmit() {
  if (!canSubmit.value || submitting.value) return
  // 检查是否有正在上传的图片
  if (uploadingCount.value > 0) {
    submitError.value = `还有 ${uploadingCount.value} 张图片正在上传，请稍候`
    return
  }
  // 检查是否有上传失败的图片
  const failedItems = photoItems.value.filter(item => item.error)
  if (failedItems.length > 0) {
    submitError.value = `有 ${failedItems.length} 张图片上传失败，请移除或重试后再提交`
    return
  }
  submitError.value = ''
  submitting.value = true
  try {
    const data = await createTicket({
      description: form.description,
      facility_type: form.facility_type,
      location_lng: form.location_lng,
      location_lat: form.location_lat,
      address: form.address || '',
      image_urls: form.image_urls.filter(u => !!u),
      emergency_level: form.emergency_level,
    })
    lastTicketId.value = data.ticket_id
    lastAiCategory.value = data.ai_category || ''
    showSuccess.value = true
    clearDraft()
    form.facility_type = ''
    form.description = ''
    form.image_urls = []
    photoItems.value.forEach(item => {
      if (item.preview) URL.revokeObjectURL(item.preview)
    })
    photoItems.value = []
    uploadError.value = ''
    form.emergency_level = 0
    loadRecentTickets()
  } catch (e) {
    submitError.value = e.message || '提交失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

async function loadRecentTickets() {
  try {
    const data = await getMyTickets({ page: 1, page_size: 3 })
    recentTickets.value = data.items || []
  } catch {}
}

function handleLogout() {
  localStorage.removeItem('citizen_token')
  localStorage.removeItem('citizen_user')
  router.replace('/login')
}
</script>

<style scoped>
.home-page {
  padding: 0 16px 24px;
  max-width: 480px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── Hero ── */
.hero {
  position: relative;
  padding: 20px 0 4px;
  text-align: center;
}
.hero-glow {
  position: absolute;
  top: -40px;
  left: 50%;
  transform: translateX(-50%);
  width: 200px;
  height: 120px;
  background: radial-gradient(ellipse, rgba(255, 137, 34, 0.08) 0%, transparent 70%);
  pointer-events: none;
}
.hero-title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 2px;
  color: var(--color-text);
  margin-bottom: 4px;
}
.hero-sub {
  font-size: 13px;
  color: var(--color-text-dim);
  letter-spacing: 0.5px;
}

/* ── 面板 ── */
.panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 16px 18px;
  transition: border-color var(--duration-normal);
}
.panel:focus-within {
  border-color: var(--color-border-glow);
}
.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.panel-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-amber);
  box-shadow: 0 0 6px rgba(255, 137, 34, 0.5);
}
.panel-dot.dim {
  background: var(--color-text-dim);
  box-shadow: none;
}
.panel-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 1.5px;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  flex: 1;
}
.panel-hint {
  font-size: 11px;
  color: var(--color-text-dim);
}
.panel-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: var(--color-green-dim);
  color: var(--color-green);
  letter-spacing: 1px;
}

/* ── 设施类型网格 ── */
.type-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.type-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 12px 4px;
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  border: 1px solid transparent;
  font-size: 11px;
  color: var(--color-text-dim);
  transition: all var(--duration-normal) var(--ease-out-expo);
}
.type-chip:active {
  transform: scale(0.95);
}
.type-chip.active {
  background: var(--color-amber-dim);
  border-color: rgba(255, 137, 34, 0.4);
  color: var(--color-amber);
  box-shadow: 0 0 12px rgba(255, 137, 34, 0.15);
}
.type-icon {
  font-size: 22px;
  transition: transform var(--duration-fast);
}
.type-chip.active .type-icon {
  transform: scale(1.15);
}
.type-name {
  font-family: var(--font-body);
  font-weight: 500;
  white-space: nowrap;
}

/* ── 描述输入 ── */
.desc-input {
  width: 100%;
  border: none;
  border-radius: var(--radius-sm);
  padding: 14px;
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text);
  background: var(--color-bg-elevated);
  resize: vertical;
  outline: none;
  border: 1px solid transparent;
  transition: border-color var(--duration-normal);
}
.desc-input:focus {
  border-color: var(--color-border-glow);
}
.desc-input::placeholder {
  color: var(--color-text-dim);
  line-height: 1.6;
}

/* ── 位置 ── */
.location-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  background: var(--color-bg-elevated);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  cursor: pointer;
  transition: all var(--duration-normal);
}
.location-box:active {
  background: var(--color-surface-hover);
}
.loc-indicator {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  flex-shrink: 0;
}
.loc-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-text-dim);
  transition: all var(--duration-normal);
}
.loc-indicator.active .loc-dot {
  background: var(--color-green);
  box-shadow: var(--color-green-glow);
}
.loc-ring {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 1px solid transparent;
  transition: all var(--duration-normal);
}
.loc-indicator.active .loc-ring {
  border-color: rgba(0, 230, 118, 0.3);
  animation: loc-pulse 2s infinite;
}
@keyframes loc-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.15); opacity: 0.5; }
}

.loc-info {
  flex: 1;
  min-width: 0;
}
.loc-text {
  font-size: 13px;
  color: var(--color-text);
  word-break: break-all;
}
.loc-placeholder {
  font-size: 13px;
  color: var(--color-text-dim);
}
.loc-action {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-dim);
  letter-spacing: 2px;
}
.loc-error {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-red);
  margin-top: 8px;
}
.error-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-red);
  box-shadow: 0 0 6px var(--color-red);
  flex-shrink: 0;
}

/* ── 紧急程度 ── */
.urgency-row {
  display: flex;
  gap: 10px;
}
.urgency-chip {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 16px 12px;
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  border: 1px solid transparent;
  color: var(--color-text-dim);
  transition: all var(--duration-normal) var(--ease-out-expo);
}
.urgency-chip.active {
  background: var(--color-green-dim);
  border-color: rgba(0, 230, 118, 0.3);
  color: var(--color-green);
}
.urgency-chip.emergency-chip.active {
  background: var(--color-red-dim);
  border-color: rgba(255, 68, 68, 0.3);
  color: var(--color-red);
}
.urgency-indicator {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.urgency-indicator.normal {
  background: rgba(0, 230, 118, 0.1);
}
.urgency-indicator.emergency {
  background: rgba(255, 68, 68, 0.1);
}
.urg-ring {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: currentColor;
}
.urgency-chip.active .urg-ring {
  box-shadow: 0 0 10px currentColor;
}
.urg-label {
  font-size: 13px;
  font-weight: 600;
}
.urg-desc {
  font-size: 10px;
  opacity: 0.7;
}

/* ── 照片 ── */
.photo-area {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.photo-thumb {
  width: 68px;
  height: 68px;
  border-radius: var(--radius-sm);
  background: var(--color-bg-elevated);
  border: 1px dashed var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  transition: border-color var(--duration-fast);
}
.photo-thumb.uploading {
  border-color: var(--color-amber);
  border-style: solid;
}
.photo-thumb.error {
  border-color: var(--color-red);
  border-style: solid;
}
.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.thumb-placeholder {
  font-size: 24px;
  opacity: 0.4;
}
/* 上传进度遮罩 */
.upload-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.55);
  display: flex;
  align-items: center;
  justify-content: center;
}
.upload-percent {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-amber);
  font-family: var(--font-mono);
}
/* 上传失败遮罩 */
.error-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 68, 68, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.error-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-red);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
/* 删除按钮 */
.delete-btn {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0,0,0,0.6);
  color: #fff;
  font-size: 11px;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  line-height: 1;
  transition: background var(--duration-fast);
}
.delete-btn:hover {
  background: var(--color-red);
}
.btn-add-photo {
  width: 68px;
  height: 68px;
  border-radius: var(--radius-sm);
  background: var(--color-bg-elevated);
  border: 1px dashed var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color var(--duration-fast);
  cursor: pointer;
}
.btn-add-photo:active {
  border-color: var(--color-amber);
}
.btn-add-photo:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.add-icon {
  font-size: 28px;
  color: var(--color-text-dim);
  font-weight: 300;
}
/* 上传错误提示 */
.upload-error {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-red);
  margin-top: 8px;
}

/* ── 提交错误 ── */
.submit-error {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-red);
  padding: 6px 0;
}

/* ── 提交按钮区域 ── */
.submit-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}

.submit-hint {
  width: 100%;
  animation: fade-up 0.3s var(--ease-out-expo);
}

.hint-card {
  background: linear-gradient(135deg, rgba(255, 137, 34, 0.1), rgba(255, 137, 34, 0.04));
  border: 1px solid rgba(255, 137, 34, 0.25);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hint-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.hint-icon {
  font-size: 16px;
}
.hint-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-amber);
  letter-spacing: 1px;
}

.hint-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.hint-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-text-secondary);
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}
.hint-bullet {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-amber);
  box-shadow: 0 0 6px rgba(255, 137, 34, 0.5);
  flex-shrink: 0;
}

@keyframes fade-up {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── 提交按钮 ── */
.btn-submit {
  width: 100%;
  height: 56px;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text-dim);
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 3px;
  transition: all var(--duration-normal) var(--ease-out-expo);
  position: relative;
  overflow: hidden;
}
.btn-submit.ready {
  background: linear-gradient(135deg, #e67a1e, #cc6000);
  border-color: transparent;
  color: #fff;
  box-shadow: var(--shadow-glow-amber);
}
.btn-submit.ready:active {
  transform: scale(0.97);
}
.btn-submit:disabled {
  cursor: not-allowed;
}
.btn-ready {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.submit-icon {
  font-size: 18px;
}
.btn-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}
.pulse-ring {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 最近工单 ── */
.recent-section {
  margin-top: 8px;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-secondary);
  letter-spacing: 1px;
}
.link-all {
  font-size: 12px;
  color: var(--color-text-dim);
  display: flex;
  align-items: center;
  gap: 4px;
  transition: color var(--duration-fast);
}
.link-all:hover {
  color: var(--color-amber);
}
.link-arrow {
  font-family: var(--font-mono);
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.recent-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: border-color var(--duration-fast), background var(--duration-fast);
}
.recent-card:active {
  background: var(--color-surface-hover);
  border-color: var(--color-border-glow);
}
.rc-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.rc-type {
  font-size: 22px;
  flex-shrink: 0;
}
.rc-info {
  min-width: 0;
}
.rc-desc {
  font-size: 13px;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
}
.rc-time {
  font-size: 11px;
  color: var(--color-text-dim);
  margin-top: 2px;
}
.rc-status {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  letter-spacing: 0.5px;
  flex-shrink: 0;
}
.st-pending { background: rgba(68,138,255,0.15); color: var(--color-blue); }
.st-dispatching { background: rgba(255,137,34,0.15); color: var(--color-amber); }
.st-repairing { background: rgba(255,184,0,0.15); color: var(--color-yellow); }
.st-verifying { background: rgba(68,138,255,0.15); color: var(--color-blue); }
.st-closed { background: rgba(0,230,118,0.15); color: var(--color-green); }

/* ── 成功弹窗 ── */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
  padding: 24px;
  animation: fade-in 0.25s ease;
}
@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }

.success-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: 36px 24px;
  text-align: center;
  max-width: 320px;
  width: 100%;
  box-shadow: var(--shadow-lg);
  animation: scale-in 0.3s var(--ease-spring);
}
@keyframes scale-in { from { transform: scale(0.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }

.success-ring {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  margin: 0 auto 16px;
  background: var(--color-green-dim);
  border: 2px solid rgba(0, 230, 118, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: success-pop 0.5s var(--ease-spring);
}
@keyframes success-pop {
  0% { transform: scale(0); }
  100% { transform: scale(1); }
}
.success-icon {
  font-size: 32px;
  color: var(--color-green);
  font-weight: 700;
  font-family: var(--font-mono);
}
.success-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 8px;
}
.success-id {
  font-size: 11px;
  color: var(--color-text-dim);
  background: var(--color-bg-elevated);
  padding: 4px 14px;
  border-radius: var(--radius-full);
  display: inline-block;
  margin-bottom: 6px;
  border: 1px solid var(--color-border);
}
.success-ai {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 20px;
}
.success-actions {
  display: flex;
  gap: 10px;
}
.btn-secondary {
  flex: 1;
  padding: 12px;
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  transition: border-color var(--duration-fast);
}
.btn-secondary:active {
  border-color: var(--color-border-glow);
}
.btn-primary {
  flex: 1;
  padding: 12px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--color-amber), #cc6600);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
  transition: transform var(--duration-fast);
}
.btn-primary:active {
  transform: scale(0.97);
}

/* ── 地图选点弹窗 ── */
.map-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: var(--color-bg);
  display: flex;
  flex-direction: column;
  animation: map-slide-up 0.3s var(--ease-out-expo);
}
@keyframes map-slide-up {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

.map-modal {
  display: flex;
  flex-direction: column;
  height: 100%;
  height: 100dvh;
}

/* 顶栏 */
.map-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  padding-top: max(12px, env(safe-area-inset-top));
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
  z-index: 10;
}
.map-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: 1px;
}
.map-btn-cancel {
  font-size: 14px;
  color: var(--color-text-secondary);
  padding: 6px 4px;
  transition: color var(--duration-fast);
}
.map-btn-cancel:active {
  color: var(--color-text);
}
.map-btn-confirm {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-dim);
  padding: 8px 16px;
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  transition: all var(--duration-normal);
}
.map-btn-confirm.active {
  color: #fff;
  background: var(--color-amber);
  border-color: transparent;
  box-shadow: 0 0 16px rgba(255, 137, 34, 0.3);
}
.map-btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 地图容器 */
.map-container {
  flex: 1;
  width: 100%;
  background: var(--color-bg-elevated);
}

/* 十字准星提示 */
.map-crosshair-hint {
  position: fixed;
  bottom: 50%;
  left: 0;
  right: 0;
  transform: translateY(50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  pointer-events: none;
  z-index: 5;
}
.crosshair-dot {
  display: none;
}
.map-crosshair-hint span:last-child {
  font-size: 11px;
  color: var(--color-text-dim);
  background: rgba(13, 15, 20, 0.8);
  padding: 4px 12px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
}

/* GPS 快捷栏 */
.map-gps-bar {
  display: flex;
  justify-content: center;
  padding: 12px 16px;
  padding-bottom: max(12px, env(safe-area-inset-bottom));
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  flex-shrink: 0;
}
.map-btn-gps {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: var(--radius-full);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 1px;
  transition: all var(--duration-normal);
}
.map-btn-gps:active {
  background: var(--color-surface-hover);
  border-color: var(--color-amber);
  color: var(--color-amber);
}
.gps-icon {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-amber);
}
</style>
