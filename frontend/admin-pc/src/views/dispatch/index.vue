<!--
  城市设施运维指挥中心 — GIS 工单调度台
  真实高德地图：设施点位 + 在线维修员 + 派单池滞留工单
-->
<template>
  <div class="dispatch-page">
    <div class="dispatch-grid">
      <!-- 地图区 -->
      <section class="map-panel">
        <header class="panel-header">
          <span class="panel-title">GIS 设施一张图</span>
          <span class="panel-badge live">● LIVE</span>
        </header>
        <div class="map-filter">
          <span class="filter-label">显示区划：</span>
          <el-select v-model="selectedDistricts" multiple placeholder="选择区划" size="small" class="district-select">
            <el-option v-for="d in ALL_DISTRICTS" :key="d" :label="d" :value="d" />
          </el-select>
          <button class="filter-btn" @click="selectedDistricts = [...ALL_DISTRICTS]">全选</button>
          <button class="filter-btn" @click="selectedDistricts = []">清空</button>
        </div>
        <div ref="mapContainer" class="map-viewport">
          <div v-if="mapStatus" class="map-status">{{ mapStatus }}</div>
          <!-- 标准/卫星切换 -->
          <div class="map-type-switch">
            <button
              class="type-btn"
              :class="{ active: currentMapType === 0 }"
              @click="switchMapType(0)"
            >标准</button>
            <button
              class="type-btn"
              :class="{ active: currentMapType === 1 }"
              @click="switchMapType(1)"
            >卫星</button>
          </div>
        </div>
        <div v-if="selectedFacility" class="facility-popup">
          <div class="popup-row"><strong>{{ selectedFacility.type }} — {{ selectedFacility.code }}</strong></div>
          <div class="popup-row mono">{{ selectedFacility.address }}</div>
          <div class="popup-row">
            <span class="status-tag" :class="selectedFacility.status">{{ statusLabels[selectedFacility.status] || selectedFacility.status }}</span>
            <span class="mono">累计 {{ selectedFacility.total_faults }} 次故障</span>
          </div>
        </div>
      </section>

      <!-- 滞留工单侧栏 -->
      <aside class="side-panel">
        <header class="panel-header">
          <span class="panel-title">派单池工单</span>
          <span class="panel-badge warn">{{ pendingTickets.length }} 待指派</span>
        </header>
        <div class="ticket-list">
          <div v-for="ticket in pendingTickets" :key="ticket.ticket_id" class="ticket-card" :class="{ emergency: ticket.emergency_level }">
            <div class="ticket-top">
              <span class="ticket-id mono">{{ ticket.ticket_id }}</span>
              <span v-if="ticket.emergency_level" class="emergency-tag">紧急</span>
            </div>
            <div class="ticket-desc">{{ (ticket.description || '').slice(0, 40) }}</div>
            <div class="ticket-meta mono"><span>{{ ticket.address }}</span></div>
            <div class="ticket-actions">
              <el-select v-model="ticket._selectedWorker" placeholder="选择维修员" size="small" class="worker-select">
                <el-option v-for="w in onlineWorkers" :key="w.worker_id" :label="w.name" :value="w.worker_id" />
              </el-select>
              <button class="btn-dispatch" @click="doDispatch(ticket)">强制指派</button>
            </div>
          </div>
          <div v-if="!pendingTickets.length" class="empty-hint">暂无派单池工单</div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
/* global AMap */
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getFacilities, getWorkers, searchTickets, forceDispatch } from '@/api/index'

const statusLabels = { normal: '正常', repairing: '维修中', scrapped: '已报废' }

const mapContainer = ref(null)
let mapInstance = null
let infoWindow = null
let facilityCluster = null
const workerMarkers = []

const onlineWorkers = ref([])
const pendingTickets = ref([])
const selectedFacility = ref(null)
const mapStatus = ref('地图加载中...')
const allFacilities = ref([])
const allWorkers = ref([])
const currentMapType = ref(0) // 0=标准, 1=卫星
let satelliteLayer = null

// 长沙各区中心（无实时位置时用于维修员兜底散布）
const DISTRICT_CENTERS = {
  '芙蓉区': [112.9895, 28.1938],
  '天心区': [112.9969, 28.1125],
  '岳麓区': [112.9438, 28.2136],
  '开福区': [112.9856, 28.2565],
  '雨花区': [113.0416, 28.1354],
  '望城区': [112.8307, 28.3614],
  '长沙县': [113.0802, 28.2469],
  '浏阳市': [113.6432, 28.1639],
  '宁乡市': [112.5538, 28.2774],
}
const ALL_DISTRICTS = Object.keys(DISTRICT_CENTERS)
const DISTRICT_COLORS = {
  '芙蓉区': '#00c48c', '天心区': '#3399ff', '岳麓区': '#ffb800',
  '开福区': '#ff6b6b', '雨花区': '#9b59b6', '望城区': '#1abc9c',
  '长沙县': '#e67e22', '浏阳市': '#3498db', '宁乡市': '#e74c3c',
}
const selectedDistricts = ref([...ALL_DISTRICTS])

function selectFacility(f) {
  selectedFacility.value = f
  if (infoWindow && mapInstance) {
    const content = `
      <div style="font-size:13px;line-height:1.6;">
        <div style="font-weight:600;">${f.type} — ${f.code}</div>
        <div style="color:#999;margin:4px 0;">${f.address}</div>
        <div>
          <span style="display:inline-block;padding:1px 6px;border-radius:2px;background:${statusColor(f.status)}20;color:${statusColor(f.status)};">
            ${statusLabels[f.status] || f.status}
          </span>
          <span style="margin-left:8px;color:#999;">累计 ${f.total_faults} 次故障</span>
        </div>
      </div>
    `
    infoWindow.setContent(content)
    infoWindow.open(mapInstance, [f.location.lng, f.location.lat])
  }
}

function statusColor(status) {
  if (status === 'normal') return '#00c48c'
  if (status === 'repairing') return '#ffb800'
  return '#ff3b3b'
}

function randomOffset(center, radius = 0.02) {
  return [
    center[0] + (Math.random() - 0.5) * radius,
    center[1] + (Math.random() - 0.5) * radius,
  ]
}

function initMap() {
  if (!window.AMap || !mapContainer.value || mapInstance) return false

  try {
    mapInstance = new window.AMap.Map(mapContainer.value, {
      center: [112.9388, 28.2282],
      zoom: 11,
    })

    infoWindow = new window.AMap.InfoWindow({
      offset: new window.AMap.Pixel(0, -10),
      closeWhenClickMap: true,
    })

    window.AMap.plugin(['AMap.Scale', 'AMap.ToolBar'], () => {
      if (!mapInstance) return
      mapInstance.addControl(new window.AMap.Scale())
      mapInstance.addControl(new window.AMap.ToolBar({
        position: 'RB',
        offset: new window.AMap.Pixel(10, 60),
      }))
    })

    window.addEventListener('resize', handleResize)
    mapStatus.value = ''
    return true
  } catch (e) {
    console.error('高德地图初始化失败:', e)
    mapStatus.value = '地图初始化失败，请刷新重试'
    return false
  }
}

function waitForAMap(callback, retries = 25) {
  if (window.AMap) {
    callback()
    return
  }
  if (retries <= 0) {
    mapStatus.value = '高德地图脚本加载失败，请检查网络或 Key 配置'
    return
  }
  setTimeout(() => waitForAMap(callback, retries - 1), 200)
}

function handleResize() {
  if (mapInstance) mapInstance.resize()
}

function switchMapType(type) {
  if (!mapInstance || !window.AMap) return
  currentMapType.value = type
  if (type === 0) {
    // 标准地图：移除卫星图层
    if (satelliteLayer) {
      satelliteLayer.setMap(null)
      satelliteLayer = null
    }
  } else {
    // 卫星地图：叠加卫星图层
    if (!satelliteLayer) {
      satelliteLayer = new window.AMap.TileLayer.Satellite()
    }
    satelliteLayer.setMap(mapInstance)
  }
}

function clearMarkers() {
  if (facilityCluster) {
    try { facilityCluster.setMap(null) } catch (e) {}
    facilityCluster = null
  }
  workerMarkers.forEach(m => { try { m.setMap(null) } catch (e) {} })
  workerMarkers.length = 0
}

function renderFacilityCluster(facs, districts) {
  if (!mapInstance || !window.AMap || !window.AMap.MarkerCluster) return
  const districtSet = new Set(districts)
  const points = facs
    .filter(f => districtSet.has(f.district) && f.location && f.location.lng && f.location.lat)
    .map(f => ({
      lnglat: [f.location.lng, f.location.lat],
      extData: f,
    }))

  facilityCluster = new window.AMap.MarkerCluster(mapInstance, points, {
    gridSize: 60,
    renderClusterMarker: (ctx) => {
      // 聚合点颜色取该簇中设施最多的区（兼容不同版本 ctx.data 字段）
      const items = Array.isArray(ctx.data)
        ? ctx.data
        : Array.isArray(ctx.points)
          ? ctx.points
          : []
      const districtCounts = {}
      items.forEach(d => {
        const ext = d && (d.extData || d.data)
        const dis = ext && ext.district
        if (dis) districtCounts[dis] = (districtCounts[dis] || 0) + 1
      })
      const mainDistrict = Object.entries(districtCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || ''
      const color = DISTRICT_COLORS[mainDistrict] || '#00c48c'
      const div = document.createElement('div')
      div.className = 'amap-facility-cluster'
      div.style.background = color
      div.style.boxShadow = `0 0 12px ${color}80`
      div.textContent = ctx.count
      ctx.marker.setContent(div)
      ctx.marker.setOffset(new window.AMap.Pixel(-14, -14))
    },
    renderMarker: (ctx) => {
      const item = ctx.data && ctx.data[0]
      const f = item && (item.extData || item.data)
      if (!f) return
      const color = DISTRICT_COLORS[f.district] || '#00c48c'
      ctx.marker.setContent(`<div class="amap-facility-dot" style="color:${color}"><div class="dot-core"></div></div>`)
      ctx.marker.setOffset(new window.AMap.Pixel(-6, -6))
      ctx.marker.on('click', () => selectFacility(f))
    },
  })
}

function renderWorkerMarkers(workers, districts) {
  if (!mapInstance || !window.AMap) return
  const districtSet = new Set(districts)
  workers.filter(w => districtSet.has(w.district)).forEach(w => {
    let pos = null
    if (w.location && w.location.lng && w.location.lat) {
      pos = [w.location.lng, w.location.lat]
    } else if (DISTRICT_CENTERS[w.district]) {
      // 无实时位置时按片区中心随机散布，避免整齐排列
      pos = randomOffset(DISTRICT_CENTERS[w.district], 0.04)
    }
    if (!pos) return
    const marker = new window.AMap.Marker({
      position: pos,
      content: `<div class="amap-worker-marker"><div class="worker-dot"></div><span class="worker-name">${w.name}</span></div>`,
      offset: new window.AMap.Pixel(-6, -6),
      zIndex: 10,
    })
    marker.setMap(mapInstance)
    workerMarkers.push(marker)
  })
}

function renderMap() {
  if (!mapInstance) initMap()
  clearMarkers()
  renderFacilityCluster(allFacilities.value, selectedDistricts.value)
  renderWorkerMarkers(allWorkers.value, selectedDistricts.value)
  if (mapInstance) {
    mapInstance.setFitView(null, false, [40, 40, 40, 40], 11)
  }
}

async function loadData() {
  try {
    // 设施（全部 1000 条）
    const facRes = await getFacilities({ page_size: 1000 })
    allFacilities.value = facRes.data.items || []

    // 在线维修员
    const wRes = await getWorkers({ page_size: 100 })
    allWorkers.value = (wRes.data.items || []).filter(w => w.is_active !== false)
    onlineWorkers.value = allWorkers.value

    // 待受理工单
    const tRes = await searchTickets({ status: 'accepting', page_size: 10 })
    pendingTickets.value = (tRes.data.items || []).map(t => ({ ...t, _selectedWorker: '' }))

    // 渲染地图
    renderMap()
  } catch (e) {
    console.error('调度台数据加载失败:', e)
  }
}

// 区划筛选变化时只重绘地图，不再请求接口
watch(selectedDistricts, () => {
  const districtSet = new Set(selectedDistricts.value)
  onlineWorkers.value = allWorkers.value.filter(w => districtSet.has(w.district))
  renderMap()
})

async function doDispatch(ticket) {
  if (!ticket._selectedWorker) { ElMessage.warning('请先选择维修员'); return }
  try {
    await forceDispatch(ticket.ticket_id, ticket._selectedWorker)
    ElMessage.success('强制指派成功')
    loadData()
  } catch (e) {
    console.error('强制指派失败:', e)
  }
}

onMounted(() => {
  waitForAMap(() => {
    initMap()
    loadData()
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (mapInstance) {
    mapInstance.destroy()
    mapInstance = null
  }
})
</script>

<style scoped>
.dispatch-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; height: calc(100vh - var(--header-height, 56px) - 48px); }
.map-panel { background: var(--bg-elevated); border: 1px solid var(--border-dim); border-radius: var(--radius-lg); display: flex; flex-direction: column; overflow: hidden; }
.panel-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; border-bottom: 1px solid var(--border-dim); }
.panel-title { font-family: var(--font-mono); font-size: 13px; font-weight: 500; letter-spacing: 1px; text-transform: uppercase; color: var(--text-secondary); }
.panel-badge { font-family: var(--font-mono); font-size: 10px; font-weight: 700; letter-spacing: 1px; }
.panel-badge.live { color: var(--signal-red); animation: blink 1.5s infinite; }
.panel-badge.warn { color: var(--signal-amber); }
.map-viewport { flex: 1; position: relative; min-height: 0; background: #0f1117; }
.map-status { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-size: 13px; z-index: 5; }
.map-filter { display: flex; align-items: center; gap: 10px; padding: 10px 16px; border-bottom: 1px solid var(--border-dim); background: var(--bg-surface); }
.filter-label { font-size: 12px; color: var(--text-secondary); white-space: nowrap; }
.district-select { width: 360px; }
:deep(.district-select .el-select__tags) { flex-wrap: wrap; max-height: 72px; overflow-y: auto; }
.filter-btn { padding: 4px 10px; background: transparent; border: 1px solid var(--border-dim); color: var(--text-secondary); border-radius: var(--radius-sm); font-size: 12px; cursor: pointer; }
.filter-btn:hover { border-color: var(--signal-amber); color: var(--signal-amber); }
.map-legend { position: absolute; bottom: 12px; left: 16px; display: flex; gap: 16px; background: rgba(15,17,23,.85); padding: 8px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-dim); }
.legend-item { font-size: 11px; color: var(--text-muted); display: flex; align-items: center; gap: 6px; }
.leg-dot { width: 8px; height: 8px; border-radius: 50%; }
.leg-dot.normal { background: var(--signal-green); } .leg-dot.repairing { background: var(--signal-yellow); }
.leg-dot.alarm { background: var(--signal-red); } .leg-dot.worker { background: var(--signal-blue); }
.facility-popup { padding: 14px 20px; border-top: 1px solid var(--border-dim); background: var(--bg-surface); }
.popup-row { margin: 4px 0; font-size: 13px; }
.status-tag { font-family: var(--font-mono); font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 2px; margin-right: 10px; }
.status-tag.normal { background: rgba(0,196,140,.15); color: var(--signal-green); }
.status-tag.repairing { background: rgba(255,184,0,.15); color: var(--signal-yellow); }
.status-tag.alarm, .status-tag.scrapped { background: rgba(255,59,59,.15); color: var(--signal-red); }
.side-panel { background: var(--bg-elevated); border: 1px solid var(--border-dim); border-radius: var(--radius-lg); display: flex; flex-direction: column; overflow: hidden; }
.ticket-list { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 10px; }
.ticket-card { background: var(--bg-surface); border: 1px solid var(--border-dim); border-radius: var(--radius-md); padding: 14px; }
.ticket-card.emergency { border-left: 3px solid var(--signal-red); }
.ticket-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.ticket-id { font-size: 12px; color: var(--text-muted); }
.emergency-tag { font-family: var(--font-mono); font-size: 10px; font-weight: 700; background: rgba(255,59,59,.15); color: var(--signal-red); padding: 2px 6px; border-radius: 2px; }
.ticket-desc { font-size: 13px; color: var(--text-primary); margin-bottom: 6px; }
.ticket-meta { font-size: 11px; color: var(--text-muted); margin-bottom: 10px; }
.ticket-actions { display: flex; gap: 8px; }
.worker-select { flex: 1; }
.btn-dispatch { padding: 6px 14px; background: var(--signal-amber); color: #fff; border: none; border-radius: var(--radius-sm); font-family: var(--font-mono); font-size: 11px; font-weight: 600; letter-spacing: 0.5px; cursor: pointer; }
.btn-dispatch:hover { background: #ff8533; }
.empty-hint { text-align: center; color: var(--text-muted); padding: 40px; font-size: 13px; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
@media (max-width: 1199px) { .dispatch-grid { grid-template-columns: 1fr; height: auto; } .map-viewport { min-height: 360px; } }
@media (max-width: 767px) { .map-viewport { min-height: 260px; } .map-legend { gap: 8px; padding: 6px 10px; font-size: 10px; } .ticket-actions { flex-direction: column; } .worker-select { width: 100%; } }

/* 标准/卫星切换按钮 */
.map-type-switch {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 5;
  display: flex;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.15);
}
.type-btn {
  padding: 5px 10px;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  border: none;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}
.type-btn:hover { background: rgba(255, 255, 255, 0.12); }
.type-btn.active { background: rgba(255, 255, 255, 0.22); font-weight: 600; }
.type-btn + .type-btn { border-left: 1px solid rgba(255, 255, 255, 0.15); }

/* 高德地图自定义标记点样式 */
:deep(.amap-facility-dot) {
  width: 12px;
  height: 12px;
  position: relative;
}
:deep(.amap-facility-dot .dot-core) {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 8px currentColor;
}
:deep(.amap-facility-cluster) {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(0, 196, 140, 0.85);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 12px rgba(0, 196, 140, 0.5);
  border: 2px solid rgba(255,255,255,0.2);
}
:deep(.amap-worker-marker) {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}
:deep(.amap-worker-marker .worker-dot) {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #3399ff;
  box-shadow: 0 0 10px rgba(51,153,255,.7);
}
:deep(.amap-worker-marker .worker-name) {
  margin-top: 2px;
  font-size: 10px;
  color: #fff;
  white-space: nowrap;
  background: rgba(0,0,0,.6);
  padding: 1px 4px;
  border-radius: 2px;
}
</style>
