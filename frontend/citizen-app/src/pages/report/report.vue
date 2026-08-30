<!--
  城市公共设施智能报修与派单系统 - 市民端AI报修提交页
  作用：自动定位、AI预填设施品类、文本实时纠错、图片压缩上传、
        重复工单智能提示（ES查重检索）
  数据流：写 MySQL tickets 主表 → MongoDB ai_analysis_logs AI解析 →
          MongoDB ticket_attachments 图片元数据 → ES tickets_index 查重 →
          Redis ticket:{tid}:info 缓存
-->
<template>
  <view class="report-form">
    <!-- 故障描述（必填核心字段） -->
    <view class="form-group">
      <text class="label">故障描述 *</text>
      <textarea v-model="description" placeholder="请描述设施故障情况（至少5个字）" :maxlength="500" />
    </view>

    <!-- 拍照上传 -->
    <view class="form-group">
      <text class="label">现场照片（选填，最多5张）</text>
      <view class="photo-grid">
        <view class="photo-item" v-for="(url, i) in photos" :key="i">
          <image :src="url" mode="aspectFill" />
          <text class="delete-btn" @click="removePhoto(i)">✕</text>
        </view>
        <view class="add-photo" v-if="photos.length < 5" @click="takePhoto">
          <text>+</text>
          <text>拍照</text>
        </view>
      </view>
    </view>

    <!-- 位置信息 -->
    <view class="form-group">
      <text class="label">故障位置</text>
      <view class="location-row">
        <text>{{ location.address || '正在获取位置...' }}</text>
        <text class="re-locate" @click="getLocation">重新定位</text>
      </view>
    </view>

    <!-- 紧急程度 -->
    <view class="form-group">
      <text class="label">紧急程度</text>
      <view class="radio-group">
        <label><radio :checked="emergency===0" @click="emergency=0" /> 普通报修</label>
        <label><radio :checked="emergency===1" @click="emergency=1" /> 紧急抢修</label>
      </view>
    </view>

    <!-- 提交按钮 -->
    <button class="submit-btn" :disabled="!canSubmit" @click="submit">提交报修</button>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { createTicket } from '../../api/ticket'

const description = ref('')
const photos = ref([])
const location = ref({ lng: 0, lat: 0, address: '' })
const emergency = ref(0)

const canSubmit = computed(() => description.value.length >= 5)

onMounted(() => { getLocation() })

const getLocation = () => {
  uni.getLocation({
    type: 'gcj02',
    success: (res) => {
      location.value = {
        lng: res.longitude,
        lat: res.latitude,
        address: `经度${res.longitude.toFixed(4)} 纬度${res.latitude.toFixed(4)}`,
      }
    },
  })
}

const takePhoto = () => {
  uni.chooseImage({
    count: 1,
    success: (res) => photos.value.push(res.tempFilePaths[0]),
  })
}

const removePhoto = (index) => photos.value.splice(index, 1)

const submit = async () => {
  try {
    const result = await createTicket({
      description: description.value,
      location_lng: location.value.lng,
      location_lat: location.value.lat,
      address: location.value.address,
      image_urls: photos.value,
      emergency_level: emergency.value,
    })
    uni.showToast({ title: `工单已受理：${result.ticket_id}` })
    uni.navigateTo({ url: `/pages/progress/progress?ticket_id=${result.ticket_id}` })
  } catch (e) { /* request.js 统一处理 */ }
}
</script>
