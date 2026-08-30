<!--
  城市公共设施智能报修与派单系统 - 市民端个人中心页
  作用：1年内报修历史列表、积分明细展示、系统消息查看、
        隐私设置管理、离线草稿管理
  数据源：MySQL tickets 历史查询、Redis counter 积分计数、
         MongoDB notifications 未读消息、本地离线草稿存储
-->
<template>
  <view class="mine-page">
    <view class="user-info">
      <image class="avatar" :src="avatarUrl" />
      <text class="nickname">{{ nickname }}</text>
      <text class="points">积分：{{ points }}</text>
    </view>

    <view class="menu-list">
      <view class="menu-item" @click="() => {}"><text>📋 我的报修记录</text></view>
      <view class="menu-item" @click="() => {}"><text>📊 积分明细</text></view>
      <view class="menu-item" @click="() => {}"><text>🔔 消息通知</text></view>
      <view class="menu-item" @click="() => {}"><text>⚙️ 隐私设置</text></view>
      <view class="menu-item" @click="handleLogout"><text>🚪 退出登录</text></view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { useUserStore } from '../../store'

const userStore = useUserStore()
const nickname = ref(userStore.nickname || '市民用户')
const avatarUrl = ref('')
const points = ref(userStore.points || 0)

const handleLogout = () => userStore.logout()
</script>
