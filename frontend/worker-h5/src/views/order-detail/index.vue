<!--
  城市公共设施智能报修与派单系统 - 维修员端工单详情页
  作用：故障原图查看、设施档案（ES facilities_index 检索）、
        AI维修方案（Dify推荐 → MongoDB ai_analysis_logs）、
        一键导航跳转（第三方地图）、周边联动工单查看（ES检索）
  数据流：MySQL tickets+facilities 关联查询、MongoDB ticket_attachments 原图、
          ES 检索周边工单、Dify 推荐方案
-->
<template>
  <view class="order-detail">
    <view class="section">
      <text class="section-title">故障详情</text>
      <text>{{ detail.description }}</text>
      <text>设施类型：{{ detail.facility_type }}</text>
      <text>地址：{{ detail.address }}</text>
    </view>

    <!-- 维修前照片 -->
    <view class="section">
      <text class="section-title">现场照片</text>
      <image v-for="url in detail.photos" :src="url" mode="widthFix" />
    </view>

    <!-- AI推荐方案 -->
    <view class="section ai-tip" v-if="detail.ai_suggestion">
      <text class="section-title">🤖 AI维修建议</text>
      <text>{{ detail.ai_suggestion }}</text>
    </view>

    <!-- 操作按钮 -->
    <view class="actions">
      <button @click="navigate">🧭 一键导航</button>
      <button @click="checkin">📍 到场签到</button>
      <button class="primary" @click="goComplete">✅ 维修完成</button>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const ticketId = route.params.ticketId
const detail = ref({})

onMounted(async () => {
  try {
    const resp = await axios.get(`/api/v1/worker/tickets/${ticketId}`)
    detail.value = resp.data.data || {}
  } catch (e) { /* 静默 */ }
})

const navigate = () => { /* 唤起第三方导航 */ }
const checkin = async () => { /* 签到逻辑 */ }
const goComplete = () => router.push(`/complete/${ticketId}`)
</script>
