// ============================================================
// 城市设施报修 · 维修工端 — API 封装
// ============================================================
import request from '@/utils/request'

// ---------- 认证 ----------
/** 用户名密码登录（统一入口，可附带 GPS 坐标） */
export function login(username, password, lng, lat) {
  return request.post('/auth/login', { username, password, lng, lat })
}

/** 修改密码 */
export function changePassword(oldPassword, newPassword) {
  return request.put('/worker/auth/change-password', { old_password: oldPassword, new_password: newPassword })
}

// ---------- 位置 ----------
/** 维修员实时位置上报 */
export function updateLocation(lng, lat) {
  return request.put('/worker/location', { lng, lat })
}

// ---------- 工单大厅 ----------
/** 获取待接工单列表（按距离排序） */
export function getTicketQueue() {
  return request.get('/worker/tickets/queue')
}

/** 一键接单 */
export function acceptTicket(ticketId) {
  return request.put(`/worker/tickets/${ticketId}/accept`)
}

// ---------- 我的工单 ----------
/** 获取我的工单列表 */
export function getMyTickets(params) {
  return request.get('/worker/tickets', { params })
}

/** 获取工单详情 */
export function getTicketDetail(ticketId) {
  return request.get(`/worker/tickets/${ticketId}`)
}

// ---------- 签到 ----------
/** 到场签到 */
export function checkinTicket(ticketId, lng, lat) {
  return request.put(`/worker/tickets/${ticketId}/checkin`, {
    ticket_id: ticketId,
    lng,
    lat,
  })
}

// ---------- 完工 ----------
/** 完工提交 */
export function completeTicket(ticketId, data) {
  return request.put(`/worker/tickets/${ticketId}/complete`, {
    ticket_id: ticketId,
    ...data,
  })
}

// ---------- 绩效 ----------
/** 查询个人绩效 */
export function getPerformance() {
  return request.get('/worker/performance')
}

// ---------- 通知 ----------
/** 获取未读通知 */
export function getUnreadNotifications() {
  return request.get('/worker/notifications/unread')
}

/** 获取所有通知（分页） */
export function getNotifications(params) {
  return request.get('/worker/notifications', { params })
}

/** 标记通知为已读 */
export function markNotificationRead(notificationId) {
  return request.put(`/worker/notifications/${notificationId}/read`)
}

/** 标记所有通知为已读 */
export function markAllNotificationsRead() {
  return request.put('/worker/notifications/read-all')
}
