<!--
  城市公共设施智能报修与派单系统 - 市民端服务评价页
  作用：星级评分（1-5星）、快捷评价标签选择、文字补充评价、
        差评申诉入口
  数据流：写 MySQL evaluations → 差评触发 RabbitMQ 延迟复核队列 →
          ES workers_perf_index 绩效联动更新
-->
<template>
  <view class="evaluate-page">
    <text class="title">评价本次维修服务</text>

    <!-- 星级评分 -->
    <view class="star-row">
      <text v-for="i in 5" :key="i" class="star" :class="{ active: i <= star }"
            @click="star = i">{{ i <= star ? '★' : '☆' }}</text>
    </view>

    <!-- 快捷标签 -->
    <view class="tag-group">
      <text v-for="tag in quickTags" :key="tag" class="tag"
            :class="{ selected: selectedTags.includes(tag) }"
            @click="toggleTag(tag)">{{ tag }}</text>
    </view>

    <!-- 文字评价 -->
    <textarea v-model="comment" placeholder="补充您的评价（选填）" :maxlength="500" />

    <!-- 提交 -->
    <button class="submit-btn" @click="submit">提交评价</button>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { submitEvaluation } from '../../api/ticket'

const ticketId = ref('')
const star = ref(5)
const selectedTags = ref([])
const comment = ref('')

const quickTags = ['响应及时', '态度好', '技术过硬', '维修彻底', '等待太长', '维修不彻底']

const toggleTag = (tag) => {
  const idx = selectedTags.value.indexOf(tag)
  if (idx > -1) selectedTags.value.splice(idx, 1)
  else selectedTags.value.push(tag)
}

const submit = async () => {
  try {
    await submitEvaluation(ticketId.value, star.value, selectedTags.value.join(','), comment.value)
    uni.showToast({ title: '感谢您的评价！' })
    setTimeout(() => uni.navigateBack(), 1500)
  } catch (e) { /* request.js 统一处理 */ }
}
</script>
