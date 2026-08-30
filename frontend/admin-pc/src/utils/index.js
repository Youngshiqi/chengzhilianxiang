// ============================================================
// 城市设施运维指挥中心 — 通用工具函数
// ============================================================

/**
 * 安全解析 JSON 字符串或直接返回数组
 * @param {any} val - 可能是 JSON 字符串或数组
 * @returns {Array}
 */
export function parseJsonArray(val) {
  if (Array.isArray(val)) return val
  try { return JSON.parse(val) } catch { return [] }
}

/**
 * 格式化时间戳为本地字符串（后端返回北京时间 naive datetime，无时区后缀）
 * @param {string|number} ts - ISO 时间戳（北京时间，无时区标记）
 * @returns {string}
 */
export function formatTime(ts) {
  if (!ts) return '-'
  try {
    // 后端返回的是北京时间但无时区后缀（如 "2026-06-24T11:36:36"）
    // JS new Date() 会把无时区的 ISO 字符串当成 UTC，导致显示少 8 小时
    // 追加 +08:00 告诉 JS 这是北京时间
    const fixed = typeof ts === 'string' && !ts.endsWith('Z') && !ts.includes('+') && !ts.includes('GMT')
      ? ts + '+08:00'
      : ts
    const d = new Date(fixed)
    const pad = n => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch { return String(ts) }
}
