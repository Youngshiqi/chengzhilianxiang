<!--
  城市设施运维指挥中心 — 数据驾驶舱
  设计：信号灯状态卡 + 扫描线实时面板 + 非对称网格
-->
<template>
  <div class="dashboard">
    <div class="scan-line"></div>

    <!-- 实时指标卡 -->
    <div class="stat-grid">
      <article v-for="card in statCards" :key="card.key" class="stat-card" :class="card.tone">
        <div class="card-sigil">{{ card.sigil }}</div>
        <div class="card-body">
          <div class="card-value mono"><span class="number">{{ card.value.toLocaleString() }}</span></div>
          <div class="card-label">{{ card.label }}</div>
        </div>
        <div class="card-trend" v-if="card.trend !== null">
          <span :class="card.trend >= 0 ? 'up' : 'down'">{{ card.trend >= 0 ? '↑' : '↓' }} {{ Math.abs(card.trend) }}%</span>
          <span class="vs">vs 昨日</span>
        </div>
        <div class="signal-lamp" :class="card.signal"></div>
      </article>
    </div>

    <!-- 工单流转 + 趋势图 -->
    <div class="panel-row">
      <section class="panel panel-flow">
        <header class="panel-header">
          <span class="panel-title">工单流转看板</span>
          <span class="panel-meta mono">实时刷新 · 当前存量</span>
        </header>
        <div class="flow-pipeline">
          <template v-for="(stage, i) in flowStages" :key="stage.key">
            <div class="flow-stage">
              <div class="stage-node" :class="stage.tone"><span class="stage-count mono">{{ stage.count }}</span></div>
              <span class="stage-label">{{ stage.label }}</span>
            </div>
            <div v-if="i < flowStages.length - 1" class="stage-arrow">→</div>
          </template>
        </div>
      </section>

      <section class="panel panel-chart">
        <header class="panel-header">
          <span class="panel-title">月度工单趋势</span>
          <span class="panel-meta mono">{{ chartRange }}</span>
        </header>
        <div ref="trendChart" class="chart-body"></div>
      </section>
    </div>

    <!-- 故障TOP + 片区分布 -->
    <div class="panel-row">
      <section class="panel">
        <header class="panel-header"><span class="panel-title">高频故障设施 TOP10</span></header>
        <div class="rank-list" v-if="topFacilities.length">
          <div v-for="(item, i) in topFacilities" :key="item.name" class="rank-item">
            <span class="rank-index" :class="{ top3: i < 3 }">{{ i + 1 }}</span>
            <span class="rank-name" :title="item.name">{{ item.name }}</span>
            <div class="rank-bar-track"><div class="rank-bar" :style="{ width: (item.count / maxTopCount * 100) + '%' }"></div></div>
            <span class="rank-count mono">{{ item.count }}</span>
          </div>
        </div>
        <div v-else class="empty-hint">暂无数据</div>
      </section>

      <section class="panel panel-district">
        <header class="panel-header"><span class="panel-title">片区工单热力</span></header>
        <div ref="districtChart" class="chart-body"></div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { getDashboardRealtime, getDashboardAnalytics } from '@/api/index'

const statCards = reactive([
  { key: 'new', sigil: '◈', label: '今日新增工单', value: 0, trend: null, tone: '', signal: 'green' },
  { key: 'pending', sigil: '◉', label: '待受理工单', value: 0, trend: null, tone: 'warn', signal: 'amber' },
  { key: 'active', sigil: '▤', label: '处理中工单', value: 0, trend: null, tone: '', signal: 'green' },
  { key: 'closed', sigil: '◎', label: '今日完结工单', value: 0, trend: null, tone: '', signal: 'green' },
])

// 定时刷新
let refreshTimer = null

const flowStages = reactive([
  { key: 'reported', label: '市民报修', count: 0, tone: 'reported' },
  { key: 'dispatching', label: 'AI派单中', count: 0, tone: 'dispatching' },
  { key: 'repairing', label: '维修进行', count: 0, tone: 'repairing' },
  { key: 'verifying', label: 'AI验收', count: 0, tone: 'verifying' },
  { key: 'closed', label: '已完结', count: 0, tone: 'closed' },
])

const topFacilities = ref([])
const districtData = ref([])
const trendData = ref([])
const maxTopCount = computed(() => Math.max(...topFacilities.value.map(t => t.count), 1))
const chartRange = ref('')

const trendChart = ref(null)
const districtChart = ref(null)
let trendChartInst = null
let districtChartInst = null

const darkTheme = {
  textStyle: { color: '#9a9da8' },
  axisLine: { lineStyle: { color: '#2e313a' } },
  splitLine: { lineStyle: { color: '#2e313a', type: 'dashed' } },
}

async function loadData() {
  try {
    const [rtRes, anRes] = await Promise.all([
      getDashboardRealtime(),
      getDashboardAnalytics(),
    ])
    const rt = rtRes.data
    statCards[0].value = rt.today_new || 0
    statCards[1].value = rt.today_dispatching || 0
    statCards[2].value = rt.today_repairing || 0
    statCards[3].value = rt.today_closed || 0

    flowStages[0].count = rt.today_new || 0
    flowStages[1].count = rt.today_dispatching || 0
    flowStages[2].count = rt.today_repairing || 0
    flowStages[3].count = rt.today_verifying || 0
    flowStages[4].count = rt.today_closed || 0

    const an = anRes.data
    topFacilities.value = an.top_facility_types || []
    districtData.value = an.district_distribution || []
    trendData.value = an.trend_data || []

    if (trendData.value.length) {
      chartRange.value = `${trendData.value[0].month} — ${trendData.value[trendData.value.length - 1].month}`
    }
    await nextTick()
    initCharts()
  } catch (e) {
    console.error('Dashboard 数据加载失败:', e)
  }
}

function initCharts() {
  initTrendChart()
  initDistrictChart()
}

function initTrendChart() {
  if (!trendChart.value || !trendData.value.length) return
  if (trendChartInst) trendChartInst.dispose()
  const chart = echarts.init(trendChart.value)
  trendChartInst = chart
  const months = trendData.value.map(d => d.month)
  const news = trendData.value.map(d => d.new_count)
  const closeds = trendData.value.map(d => d.closed_count)
  chart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: '#1a1d23', borderColor: '#2e313a', textStyle: { color: '#e4e6eb' } },
    legend: { bottom: 0, textStyle: { color: '#9a9da8' }, data: ['新增', '完结'] },
    grid: { left: 50, right: 24, top: 20, bottom: 50 },
    xAxis: { type: 'category', data: months, axisLine: darkTheme.axisLine, axisTick: { show: false }, axisLabel: { color: '#5e616d', fontFamily: 'DM Mono' } },
    yAxis: { type: 'value', splitLine: darkTheme.splitLine, axisLabel: { color: '#5e616d', fontFamily: 'DM Mono' } },
    series: [
      { name: '新增', type: 'line', data: news, smooth: true, symbol: 'circle', symbolSize: 6, lineStyle: { color: '#ff6a00', width: 2 }, itemStyle: { color: '#ff6a00' }, areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(255,106,0,.2)'},{offset:1,color:'rgba(255,106,0,0)'}]) }},
      { name: '完结', type: 'line', data: closeds, smooth: true, symbol: 'circle', symbolSize: 6, lineStyle: { color: '#00c48c', width: 2 }, itemStyle: { color: '#00c48c' }, areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(0,196,140,.15)'},{offset:1,color:'rgba(0,196,140,0)'}]) }},
    ],
  })
}

function initDistrictChart() {
  if (!districtChart.value || !districtData.value.length) return
  if (districtChartInst) districtChartInst.dispose()
  const chart = echarts.init(districtChart.value)
  districtChartInst = chart
  const names = districtData.value.map(d => d.name)
  const values = districtData.value.map(d => d.count)
  chart.setOption({
    tooltip: { trigger: 'item', backgroundColor: '#1a1d23', borderColor: '#2e313a', textStyle: { color: '#e4e6eb' } },
    grid: { left: 64, right: 36, top: 10, bottom: 10 },
    xAxis: { type: 'value', splitLine: darkTheme.splitLine, axisLabel: { color: '#5e616d', fontFamily: 'DM Mono', fontSize: 10 } },
    yAxis: { type: 'category', data: names, axisLine: darkTheme.axisLine, axisLabel: { color: '#9a9da8', fontSize: 12 }, axisTick: { show: false } },
    series: [{ type: 'bar', data: values, barWidth: 14, itemStyle: { borderRadius: [0,3,3,0], color: new echarts.graphic.LinearGradient(0,0,1,0,[{offset:0,color:'#ff6a00'},{offset:1,color:'#ff914d'}]) }, label: { show: true, position: 'right', color: '#9a9da8', fontFamily: 'DM Mono', fontSize: 11 } }],
  })
}

function handleResize() {
  if (trendChartInst) trendChartInst.resize()
  if (districtChartInst) districtChartInst.resize()
}

onMounted(() => {
  loadData()
  // 每 15 秒自动刷新仪表盘数据
  refreshTimer = setInterval(loadData, 15000)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null }
  window.removeEventListener('resize', handleResize)
  if (trendChartInst) trendChartInst.dispose()
  if (districtChartInst) districtChartInst.dispose()
})
</script>

<style scoped>
.scan-line { position: fixed; top: 0; left: var(--sidebar-width); right: 0; height: 2px; background: linear-gradient(90deg, transparent, rgba(255,106,0,.4), transparent); z-index: 10; animation: scan-down 4s linear infinite; pointer-events: none; }
@keyframes scan-down { 0% { top: var(--header-height); opacity: 0; } 10% { opacity: 1; } 90% { opacity: 1; } 100% { top: 100%; opacity: 0; } }
.dashboard { position: relative; display: flex; flex-direction: column; gap: 20px; }
.stat-grid { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 16px; }
.stat-card { background: var(--bg-elevated); border: 1px solid var(--border-dim); border-radius: var(--radius-lg); padding: 20px 24px; position: relative; overflow: hidden; transition: all var(--duration-normal) var(--ease-out-expo); }
.stat-card:hover { border-color: var(--border-active); box-shadow: var(--shadow-elevated); }
.stat-card:first-child { background: linear-gradient(135deg, rgba(255,106,0,.08), rgba(255,106,0,.02)); border-color: rgba(255,106,0,.3); }
.stat-card.warn { background: linear-gradient(135deg, rgba(255,184,0,.06), rgba(255,184,0,0)); border-color: rgba(255,184,0,.25); }
.card-sigil { font-size: 28px; color: var(--text-muted); position: absolute; top: 12px; right: 16px; opacity: .3; }
.card-body { position: relative; z-index: 1; }
.card-value { margin-bottom: 6px; }
.number { font-size: 42px; font-weight: 300; letter-spacing: -2px; color: var(--text-primary); }
.stat-card.warn .number { color: var(--signal-yellow); }
.card-label { font-size: 13px; color: var(--text-secondary); letter-spacing: 0.5px; }
.card-trend { margin-top: 10px; font-size: 12px; }
.up { color: var(--signal-green); } .down { color: var(--signal-red); } .vs { color: var(--text-muted); margin-left: 4px; }
.signal-lamp { position: absolute; top: 16px; right: 16px; width: 10px; height: 10px; border-radius: 50%; }
.signal-lamp.green { background: var(--signal-green); box-shadow: 0 0 10px var(--signal-green); }
.signal-lamp.amber { background: var(--signal-yellow); box-shadow: 0 0 10px var(--signal-yellow); animation: blink 1.5s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
.panel-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.panel { background: var(--bg-elevated); border: 1px solid var(--border-dim); border-radius: var(--radius-lg); padding: 20px 24px; }
.panel-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 16px; }
.panel-title { font-family: var(--font-mono); font-size: 13px; font-weight: 500; letter-spacing: 1px; text-transform: uppercase; color: var(--text-secondary); }
.panel-meta { font-size: 11px; color: var(--text-muted); }
.chart-body { height: 260px; }
.flow-pipeline { display: flex; align-items: center; justify-content: space-between; padding: 10px 0; }
.flow-stage { display: flex; flex-direction: column; align-items: center; gap: 10px; flex: 1; }
.stage-node { width: 52px; height: 52px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid var(--border-active); background: var(--bg-surface); }
.stage-node.reported { border-color: var(--signal-blue); background: rgba(51,153,255,.1); }
.stage-node.dispatching { border-color: var(--signal-amber); background: rgba(255,106,0,.1); }
.stage-node.repairing { border-color: var(--signal-yellow); background: rgba(255,184,0,.1); }
.stage-node.verifying { border-color: var(--signal-blue); background: rgba(51,153,255,.08); }
.stage-node.closed { border-color: var(--signal-green); background: rgba(0,196,140,.1); }
.stage-count { font-size: 16px; font-weight: 500; }
.stage-label { font-size: 11px; color: var(--text-muted); text-align: center; white-space: nowrap; }
.stage-arrow { color: var(--text-muted); font-size: 18px; flex-shrink: 0; margin: 0 4px; align-self: flex-start; margin-top: 16px; }
.rank-list { display: flex; flex-direction: column; gap: 6px; }
.rank-item { display: flex; align-items: center; gap: 10px; padding: 6px 0; }
.rank-index { width: 22px; text-align: center; font-family: var(--font-mono); font-size: 12px; color: var(--text-muted); }
.rank-index.top3 { color: var(--signal-amber); font-weight: 700; }
.rank-name { flex-shrink: 0; width: 110px; font-size: 13px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-bar-track { flex: 1; height: 6px; background: var(--bg-surface); border-radius: 3px; overflow: hidden; }
.rank-bar { height: 100%; background: linear-gradient(90deg, var(--signal-amber), var(--signal-blue)); border-radius: 3px; transition: width 1s var(--ease-out-expo); }
.rank-count { font-family: var(--font-mono); font-size: 13px; color: var(--text-primary); width: 36px; text-align: right; }
.empty-hint { text-align: center; color: var(--text-muted); padding: 40px; font-size: 14px; }
@media (max-width: 1400px) { .stat-grid { grid-template-columns: 1fr 1fr; } .panel-row { grid-template-columns: 1fr; } .flow-pipeline { flex-wrap: wrap; gap: 10px; } }
@media (max-width: 767px) { .stat-grid { grid-template-columns: 1fr; } .number { font-size: 32px; } .card-sigil { display: none; } .signal-lamp { top: 8px; right: 10px; width: 8px; height: 8px; } .panel { padding: 14px 16px; } .chart-body { height: 200px; } }
</style>
