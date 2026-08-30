// ============================================================
// 城市公共设施报修与派单系统 - 市民端 API 封装
// ============================================================
import request from '@/utils/request'

export function login(username, password) {
  return request.post('/auth/login', { username, password })
}

export function register(data) {
  return request.post('/auth/register', data)
}

export function sendSmsCode(phoneNumber, scene = 'login') {
  return request.post('/auth/send-sms-code', { phone_number: phoneNumber, scene })
}

export function smsLogin(phoneNumber, verifyCode) {
  return request.post('/auth/sms-login', { phone_number: phoneNumber, verify_code: verifyCode })
}

export function createTicket(data) {
  return request.post('/citizen/tickets', data)
}

export function getTicketDetail(id) {
  return request.get(`/citizen/tickets/${id}`)
}

export function getMyTickets(params) {
  return request.get('/citizen/tickets', { params })
}

export function closeTicket(id) {
  return request.put(`/citizen/tickets/${id}/close`)
}

export function cancelTicket(id) {
  return request.put(`/citizen/tickets/${id}/cancel`)
}

export function reverseGeocode(lng, lat) {
  return request.get('/utils/reverse-geocode', { params: { lng, lat } })
}

export function submitEvaluation(data) {
  return request.post('/citizen/evaluations', data)
}
