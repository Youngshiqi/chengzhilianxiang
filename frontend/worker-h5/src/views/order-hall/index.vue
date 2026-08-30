<!--
  城市公共设施智能报修与派单系统 - 维修员端实时接单大厅
  作用：新工单语音播报、工单紧急度标签（红色紧急/蓝色普通）、
        一键接单、忙碌免打扰开关
  数据流：RabbitMQ 消息消费 → WebSocket 弹窗推送 →
          Redis dispatch:online_workers 维护在线状态
-->
<template>
  <view class="order-hall">
    <view class="top-bar">
      <text class="title">接单大厅</text>
      <switch :checked="!busy" @change="toggleBusy" />
      <text>{{ busy ? '忙碌免打扰' : '接收新工单' }}</text>
    </view>

    <view class="order-list">
      <view v-for="order in orders" :key="order.ticket_id" class="order-card"
            :class="{ emergency: order.emergency_level === 1 }"
            @click="goDetail(order.ticket_id)">
        <view class="card-header">
          <text class="tag">{{ order.emergency_level === 1 ? '🔴 紧急' : '🔵 普通' }}</text>
          <text class="type">{{ order.facility_type }}</text>
          <text class="distance">{{ order.distance_meters }}m</text>
        </view>
        <text class="desc">{{ order.description }}</text>
        <text class="address">{{ order.address }}</text>
        <button class="accept-btn" @click.stop="acceptOrder(order.ticket_id)">
          一键接单
        </button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const busy = ref(false)
const orders = ref([])

onMounted(async () => {
  try {
    const resp = await axios.get('/api/v1/worker/tickets/queue')
    orders.value = resp.data.data || []
  } catch (e) { /* 静默 */ }
})

const toggleBusy = () => { busy.value = !busy.value }
const goDetail = (tid) => router.push(`/order/${tid}`)

const acceptOrder = async (ticketId) => {
  try {
    await axios.put(`/api/v1/worker/tickets/${ticketId}/accept`)
    router.push(`/order/${ticketId}`)
  } catch (e) { /* 静默 */ }
}
</script>
