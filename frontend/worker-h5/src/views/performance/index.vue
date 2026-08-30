<!--
  城市公共设施智能报修与派单系统 - 维修员端绩效中心
  作用：日/周/月工单统计、好评排行、结算预估金额、
        违规扣分台账展示
  数据源：ES workers_perf_index 聚合绩效 →
          Redis worker:{id}:daily_order 实时计数 →
          MySQL settlements 结算预估
-->
<template>
  <view class="performance-page">
    <view class="stats-grid">
      <view class="stat-item"><text class="num">{{ todayOrders }}</text><text>今日工单</text></view>
      <view class="stat-item"><text class="num">{{ monthOrders }}</text><text>本月工单</text></view>
      <view class="stat-item"><text class="num">{{ avgStar }}⭐</text><text>好评率</text></view>
      <view class="stat-item"><text class="num">¥{{ estimate }}</text><text>预估结算</text></view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const todayOrders = ref(0)
const monthOrders = ref(0)
const avgStar = ref(0)
const estimate = ref(0)

onMounted(async () => {
  try {
    const resp = await axios.get('/api/v1/worker/performance')
    const d = resp.data.data
    todayOrders.value = d?.today_orders || 0
    monthOrders.value = d?.month_orders || 0
    avgStar.value = d?.avg_star || 0
    estimate.value = d?.settlement_estimate || 0
  } catch (e) { /* 静默 */ }
})
</script>
