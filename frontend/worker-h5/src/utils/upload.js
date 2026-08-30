// ============================================================
// 城市设施报修 · 维修工端 — 图片上传工具（服务端转发至 OSS）
// 作用：前端 FormData 发送文件 → 后端接收并写入 OSS → 返回 URL
// ============================================================
import request from './request'

const MAX_SIZE_MB = 10
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']

/**
 * 压缩图片（超过 maxSizeMB 时等比缩放）
 */
function compressIfNeeded(file, maxSizeMB = 2) {
  const maxBytes = maxSizeMB * 1024 * 1024
  if (file.size <= maxBytes) return Promise.resolve(file)

  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      const ratio = Math.sqrt(maxBytes / file.size)
      const w = Math.round(img.width * ratio)
      const h = Math.round(img.height * ratio)

      const canvas = document.createElement('canvas')
      canvas.width = w
      canvas.height = h
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0, w, h)

      canvas.toBlob(
        (blob) => resolve(blob || file),
        file.type || 'image/jpeg',
        0.85,
      )
    }
    img.onerror = () => resolve(file)
    img.src = URL.createObjectURL(file)
  })
}

/**
 * 上传图片到服务端（服务端转发至阿里云 OSS）
 * @param {File} file — 用户选择的图片文件
 * @param {Function} [onProgress] — 进度回调 (percent: number)
 * @returns {Promise<string>} OSS 公网访问 URL
 */
export async function uploadImage(file, onProgress) {
  // 1. 校验类型
  if (!ALLOWED_TYPES.includes(file.type)) {
    throw new Error(`不支持的图片格式：${file.type || '未知'}，仅支持 JPG/PNG/GIF/WebP/BMP`)
  }

  // 2. 校验大小
  if (file.size > MAX_SIZE_MB * 1024 * 1024) {
    throw new Error(`图片过大（${(file.size / 1024 / 1024).toFixed(1)}MB），最大 ${MAX_SIZE_MB}MB`)
  }

  // 3. 压缩（>2MB 自动缩放）
  const blob = await compressIfNeeded(file, 2)

  // 4. 构建 FormData
  const formData = new FormData()
  formData.append('file', blob, file.name || 'image.jpg')

  // 5. 上传到后端
  const data = await request.post('/utils/upload-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress) {
        if (e.total && e.total > 0) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        } else if (e.loaded && e.loaded > 0) {
          // total 为 0 时（小文件/某些代理），用 loaded 占位，最终由调用方设 100%
          onProgress(Math.min(Math.round(e.loaded / 1024), 90))
        }
      }
    },
  })

  if (!data || !data.url) {
    throw new Error('上传失败，服务器未返回图片地址')
  }

  return data.url
}
