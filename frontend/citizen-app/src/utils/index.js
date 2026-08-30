// ============================================================
// 城市设施报修 · 市民端 — 工具函数
// ============================================================

/** 格式化时间 */
export function formatTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** 状态映射 */
export const STATUS_MAP = {
  pending: { label: '待受理', color: '#5198ff' },
  accepting: { label: '派单中', color: '#ff8522' },
  dispatching: { label: '已接单', color: '#9c27b0' },
  repairing: { label: '维修中', color: '#ffb800' },
  verifying: { label: '验收中', color: '#5198ff' },
  closed: { label: '已完结', color: '#2ecc71' },
  cancelled: { label: '已撤销', color: '#999' },
}

/** 设施类型图标映射 */
export const FACILITY_ICONS = {
  '路灯': '💡', '井盖': '🕳️', '护栏': '🚧', '信号灯': '🚦',
  '公交站牌': '🚏', '消防栓': '🧯', '公厕': '🚻', '指示牌': '🪧',
  '垃圾桶': '🗑️', '健身器材': '🏋️', '其他': '🔧',
}

/** 获取设施图标 */
export function getFacilityIcon(type) {
  return FACILITY_ICONS[type] || '🔧'
}
