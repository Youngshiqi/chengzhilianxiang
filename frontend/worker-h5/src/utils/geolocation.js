// 城市设施报修 · 维修工端 — 高精度定位工具
// 统一管理高德SDK和原生GPS定位，支持精度验证和持续监听

let watcherId = null
let lastValidPosition = null

// 定位配置
const DEFAULT_OPTIONS = {
  enableHighAccuracy: true,
  timeout: 15000,
  maximumAge: 5000,
}

// 精度验证阈值（米）
export const ACCURACY_THRESHOLD = {
  CHECKIN: 50,    // 签到需要高精度
  NORMAL: 100,    // 普通上报可以宽松一点
}

/**
 * 获取当前位置 - 优先使用高德SDK
 */
export function getCurrentPosition(options = {}) {
  return new Promise((resolve, reject) => {
    const mergedOptions = { ...DEFAULT_OPTIONS, ...options }

    // 优先尝试高德SDK
    if (window.AMap && typeof AMap.plugin === 'function') {
      try {
        AMap.plugin('AMap.Geolocation', () => {
          const geo = new AMap.Geolocation({
            enableHighAccuracy: mergedOptions.enableHighAccuracy,
            timeout: mergedOptions.timeout,
            noIpLocate: 0,
            noGeoLocation: 0,
          })
          geo.getCurrentPosition((status, result) => {
            if (status === 'complete' && result.position) {
              const pos = {
                lng: result.position.lng,
                lat: result.position.lat,
                accuracy: result.accuracy || 999,
                source: 'amap',
              }
              lastValidPosition = pos
              resolve(pos)
            } else {
              // 高德失败，降级到原生
              getNativePosition(mergedOptions).then(resolve).catch(reject)
            }
          })
        })
      } catch (e) {
        // 高德异常，降级到原生
        getNativePosition(mergedOptions).then(resolve).catch(reject)
      }
    } else {
      // 没有高德，使用原生
      getNativePosition(mergedOptions).then(resolve).catch(reject)
    }
  })
}

/**
 * 原生GPS定位
 */
function getNativePosition(options) {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('浏览器不支持定位'))
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const position = {
          lng: pos.coords.longitude,
          lat: pos.coords.latitude,
          accuracy: pos.coords.accuracy,
          source: 'native',
        }
        lastValidPosition = position
        resolve(position)
      },
      (err) => {
        reject(err)
      },
      options
    )
  })
}

/**
 * 开始持续监听位置变化 - 用于实时位置上报
 */
export function startWatchPosition(callback) {
  if (!navigator.geolocation) {
    return null
  }

  // 如果已有监听器，先停止
  if (watcherId !== null) {
    stopWatchPosition()
  }

  watcherId = navigator.geolocation.watchPosition(
    (pos) => {
      const position = {
        lng: pos.coords.longitude,
        lat: pos.coords.latitude,
        accuracy: pos.coords.accuracy,
        source: 'native-watch',
      }
      lastValidPosition = position
      callback && callback(position)
    },
    null, // 错误不处理，继续使用上一次有效位置
    DEFAULT_OPTIONS
  )

  return watcherId
}

/**
 * 停止监听位置变化
 */
export function stopWatchPosition() {
  if (watcherId !== null && navigator.geolocation) {
    navigator.geolocation.clearWatch(watcherId)
    watcherId = null
  }
}

/**
 * 获取最后一次有效位置
 */
export function getLastPosition() {
  return lastValidPosition
}

/**
 * 高精度定位 - 用于签到等关键场景
 * 会尝试多次获取直到满足精度要求或超时
 */
export async function getHighAccuracyPosition(maxWaitMs = 20000) {
  const startTime = Date.now()
  let lastPos = null

  while (Date.now() - startTime < maxWaitMs) {
    try {
      const pos = await getCurrentPosition()
      lastPos = pos
      // 如果精度满足要求，直接返回
      if (pos.accuracy <= ACCURACY_THRESHOLD.CHECKIN) {
        return {
          ...pos,
          isAccurate: true,
        }
      }
    } catch (e) {
      // 本次失败，继续尝试
    }
    // 等待2秒再试
    await new Promise(resolve => setTimeout(resolve, 2000))
  }

  // 超时，返回最后一次获取的位置（可能精度不够）
  if (lastPos) {
    return {
      ...lastPos,
      isAccurate: lastPos.accuracy <= ACCURACY_THRESHOLD.CHECKIN,
    }
  }

  throw new Error('无法获取位置')
}

/**
 * 验证位置精度是否足够
 */
export function isAccurateEnough(pos, threshold = ACCURACY_THRESHOLD.CHECKIN) {
  if (!pos) return false
  return pos.accuracy <= threshold
}

export default {
  getCurrentPosition,
  getHighAccuracyPosition,
  startWatchPosition,
  stopWatchPosition,
  getLastPosition,
  isAccurateEnough,
  ACCURACY_THRESHOLD,
}
