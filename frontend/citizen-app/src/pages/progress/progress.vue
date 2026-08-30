<!--
  城市公共设施智能报修与派单系统 - 市民端工单进度页
  作用：全流程时间轴展示、脱敏维修员点位（GPS偏移）、工单流转节点备注、
        消息回溯查看
  数据源：Redis ticket:{tid}:info 热缓存（Miss降级MySQL）→ WebSocket实时推送
-->
<template>
  <view class="progress-page">
    <view class="ticket-header">
      <text class="ticket-id">工单号：{{ ticketId }}</text>
      <text class="status-badge">{{ statusMap[status] || status }}</text>
    </view>

    <!-- 时间轴 -->
    <view class="timeline">
      <view class="timeline-item" v-for="(node, i) in timeline" :key="i">
        <view class="dot" :class="{ active: node.active }" />
        <view class="content">
          <text class="title">{{ node.title }}</text>
          <text class="time">{{ node.time }}</text>
          <text class="desc">{{ node.desc }}</text>
        </view>
      </view>
    </view>

    <!-- 维修员位置（脱敏展示） -->
    <view v-if="status === 'repairing'" class="worker-location">
      <text>维修员正在赶往现场（位置已脱敏）</text>
    </view>

    <!-- 评价入口 -->
    <button v-if="status === 'verifying'" class="eval-btn" @click="goEvaluate">
      评价本次服务
    </button>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getTicketProgress } from '../../api/ticket'

const ticketId = ref('')
const status = ref('pending')
const timeline = ref([])

const statusMap = {
  pending: '待受理',
  accepting: '派单中',
  dispatching: '已接单',
  repairing: '维修中',
  verifying: '验收中',
  closed: '已完结',
}

onMounted(async () => {
  // 从路由参数获取 ticket_id
  const pages = getCurrentPages()
  const params = pages[pages.length - 1].options || {}
  ticketId.value = params.ticket_id || ''

  if (ticketId.value) {
    try {
      const data = await getTicketProgress(ticketId.value)
      status.value = data?.status || 'pending'
    } catch (e) { /* 静默失败 */ }
  }
})

const goEvaluate = () => {
  uni.navigateTo({ url: `/pages/evaluate/evaluate?ticket_id=${ticketId.value}` })
}
</script>
