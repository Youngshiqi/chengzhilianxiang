<!--
  城市公共设施智能报修与派单系统 - 市民端首页
  作用：居中快速报修按钮、近期工单快捷入口、个人积分展示、
        系统公告弹窗、微信授权登录入口
  数据源：MySQL users 读取用户信息、Redis counter 积分读取、
         MySQL tickets 查询最近工单
-->
<template>
  <view class="home">
    <!-- 顶部区域 -->
    <view class="header">
      <text class="app-name">城市设施报修</text>
      <text class="slogan">共建智慧城市，随手报修故障</text>
    </view>

    <!-- 快速报修大按钮 -->
    <view class="report-btn" @click="goReport">
      <text class="icon">📷</text>
      <text class="text">一键报修</text>
      <text class="sub">拍照/文字描述 · AI智能识别</text>
    </view>

    <!-- 功能入口 -->
    <view class="menu-grid">
      <view class="menu-item" @click="goMyTickets">
        <text class="icon">📋</text>
        <text>我的工单</text>
      </view>
      <view class="menu-item" @click="goMine">
        <text class="icon">👤</text>
        <text>个人中心</text>
      </view>
    </view>

    <!-- 近期工单 -->
    <view class="recent-section" v-if="recentTickets.length">
      <text class="section-title">近期工单</text>
      <view class="ticket-item" v-for="ticket in recentTickets" :key="ticket.ticket_id"
            @click="goProgress(ticket.ticket_id)">
        <text>{{ ticket.description?.substring(0, 30) }}...</text>
        <text class="status">{{ ticket.status }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onShow } from 'vue'
import { getMyTickets } from '../api/ticket'

const recentTickets = ref([])

onShow(async () => {
  try {
    const data = await getMyTickets(1, 5)
    recentTickets.value = data?.items || []
  } catch (e) { /* 静默失败 */ }
})

const goReport = () => uni.navigateTo({ url: '/pages/report/report' })
const goMyTickets = () => uni.navigateTo({ url: '/pages/progress/progress' })
const goMine = () => uni.navigateTo({ url: '/pages/mine/mine' })
const goProgress = (id) => uni.navigateTo({ url: `/pages/progress/progress?ticket_id=${id}` })
</script>
