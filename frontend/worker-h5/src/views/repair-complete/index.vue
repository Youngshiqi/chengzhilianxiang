<!--
  城市公共设施智能报修与派单系统 - 维修工端完工闭环页
  作用：水印拍照（GPS+时间戳自动加盖，生成watermark_hash）、
        耗材录入（名称/数量+单价，数组灵活存储）、工时填报、
        完工提交 → Dify AI验收对比 → MongoDB ai_analysis_logs →
        MySQL tickets.status → verifying
  数据流：MongoDB repair_records 存耗材数组 →
          MongoDB ticket_attachments 存完工图片元数据 →
          Dify AI验收结果写 MongoDB → MySQL 工单状态更新
-->
<template>
  <view class="repair-complete">
    <!-- 完工拍照（水印加持） -->
    <view class="section">
      <text class="section-title">完工拍照</text>
      <view class="photo-grid">
        <image v-for="(url, i) in afterPhotos" :src="url" mode="aspectFill" />
        <view class="add-photo" @click="takePhoto">+ 拍照</view>
      </view>
    </view>

    <!-- 耗材录入 -->
    <view class="section">
      <text class="section-title">耗材使用</text>
      <view v-for="(m, i) in materials" :key="i" class="material-row">
        <input v-model="m.name" placeholder="请输入耗材名称（如：LED灯泡）" />
        <input v-model.number="m.qty" placeholder="数量" type="number" />
        <input v-model.number="m.unit_cost" placeholder="单价（元）" type="digit" />
        <text class="delete-btn" @click="materials.splice(i, 1)">✕</text>
      </view>
      <button @click="materials.push({name:'',qty:0,unit_cost:0})">+ 添加耗材</button>
    </view>

    <!-- 工时 -->
    <view class="section">
      <text class="section-title">维修工时（小时）</text>
      <input v-model.number="laborHours" type="digit" placeholder="例如：2.5" />
    </view>

    <!-- 备注 -->
    <textarea v-model="notes" placeholder="维修备注（选填）" />

    <!-- 提交 -->
    <button class="submit-btn" @click="submit">提交完工</button>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const ticketId = route.params.ticketId
const afterPhotos = ref([])
const materials = ref([{ name: '', qty: 0, unit_cost: 0 }])
const laborHours = ref(0)
const notes = ref('')

const takePhoto = () => { /* 拍照+水印+上传OSS */ }
const submit = async () => {
  try {
    await axios.put(`/api/v1/worker/tickets/${ticketId}/complete`, {
      ticket_id: ticketId,
      materials: materials.value.filter(m => m.name),
      labor_hours: laborHours.value,
      work_notes: notes.value,
      completion_photo_urls: afterPhotos.value,
    })
    alert('完工提交成功，等待AI验收')
  } catch (e) { /* 静默 */ }
}
</script>
