// ============================================================
// 城市设施运维指挥中心 — API 接口封装
// 所有管理后台 API 调用函数
// ============================================================

import request from './request'

// ---------- 认证 ----------
export function login(username, password) {
  return request.post('/auth/login', { username, password })
}

// ---------- 驾驶舱 ----------
export function getDashboardRealtime() {
  return request.get('/admin/dashboard/realtime')
}

export function getDashboardAnalytics() {
  return request.get('/admin/dashboard/analytics')
}

// ---------- 工单 ----------
export function searchTickets(params) {
  return request.get('/admin/tickets/search', { params })
}

export function forceDispatch(ticketId, workerId) {
  return request.post(`/admin/tickets/${ticketId}/dispatch`, { ticket_id: ticketId, worker_id: workerId })
}

export function getTicketDetail(ticketId) {
  return request.get(`/admin/tickets/${ticketId}`)
}

// ---------- 人员 ----------
export function getWorkers(params) {
  return request.get('/admin/workers', { params })
}

export function getWorkerSkills() {
  return request.get('/admin/workers/skills')
}

export function updateWorker(workerId, data) {
  return request.put(`/admin/workers/${workerId}`, data)
}

export function createWorker(data) {
  return request.post('/admin/workers', data)
}

// ---------- 设施 ----------
export function getFacilities(params) {
  return request.get('/admin/facilities', { params })
}

// ---------- 结算 ----------
export function getSettlements(params) {
  return request.get('/admin/settlements', { params })
}

export function auditSettlement(settlementId, action, remark = '') {
  return request.put(`/admin/settlements/${settlementId}/audit`, {
    settlement_id: settlementId, action, remark
  })
}

// ---------- 审计 ----------
export function getAuditLogs(params) {
  return request.get('/admin/audit-logs', { params })
}

// ---------- 配置 ----------
export function getConfig() {
  return request.get('/admin/config')
}

export function updateConfig(items) {
  return request.put('/admin/config', { items })
}

export function createConfig(data) {
  return request.post('/admin/config', data)
}
