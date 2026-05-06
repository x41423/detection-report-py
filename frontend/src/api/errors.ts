const ERROR_CODE_MESSAGES: Record<string, string> = {
  ACCOUNT_DISABLED: '账号已被停用',
  ACCOUNT_LOCKED: '账号已被临时锁定',
  AUTH_REQUIRED: '请先登录',
  CANNOT_DISABLE_SELF: '不能停用自己的账号',
  DEVICE_LIMIT_REACHED: '设备数量已达上限，请选择旧设备替换后再登录',
  DEVICE_NOT_FOUND: '设备不存在',
  INVALID_CREDENTIALS: '用户名或密码错误',
  INVALID_DEVICE_NAME: '设备名称不合法',
  INVALID_PASSWORD: '密码不符合要求',
  INVALID_PERMISSION: '权限不合法',
  INVALID_REFRESH_TOKEN: '刷新登录凭证无效或已撤销',
  INVALID_REQUEST_STATUS: '权限申请状态无效',
  INVALID_REVIEW_STATUS: '审批结果无效',
  INVALID_ROLE: '角色不合法',
  INVALID_ROLE_CODE: '角色编码不合法',
  INVALID_TOKEN: '登录状态无效或已撤销',
  INVALID_USERNAME: '用户名不符合要求',
  PENDING_LOGIN_EXPIRED: '待确认登录凭证已过期',
  PENDING_LOGIN_INVALID: '待确认登录凭证无效或已使用',
  PENDING_LOGIN_REQUIRED: '缺少待确认登录凭证',
  PERMISSION_ALREADY_GRANTED: '你已拥有该权限',
  PERMISSION_DENIED: '当前账号没有执行此操作的权限',
  PERMISSION_NOT_FOUND: '权限不存在',
  PERMISSION_REQUEST_NOT_FOUND: '权限申请不存在',
  PERMISSION_REQUEST_NOT_PENDING: '该权限申请已处理，不能重复审批',
  PERMISSION_REQUEST_PENDING: '该权限已有待审批申请',
  REFRESH_REQUIRED: '登录状态已失效，请重新登录',
  REFRESH_TOKEN_EXPIRED: '登录状态已过期，请重新登录',
  RESERVED_ROLE: '超级管理员角色为系统保留角色',
  ROLE_EXISTS: '角色已存在',
  ROLE_IN_USE: '仍有用户正在使用该角色',
  ROLE_NOT_FOUND: '角色不存在',
  SUPER_ADMIN_PROTECTED: '只有超级管理员可以修改超级管理员账号',
  SUPER_ADMIN_ROLE_LOCKED: '超级管理员角色不能被修改',
  SYSTEM_ROLE_PROTECTED: '系统角色不能删除',
  TOKEN_EXPIRED: '登录状态已过期，请重新登录',
  USER_NOT_FOUND: '用户不存在',
  USERNAME_EXISTS: '用户名已存在',
}

export function getApiErrorMessage(error: unknown, fallback: string = '请求失败'): string {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof (error as { response?: unknown }).response === 'object' &&
    (error as { response?: { data?: unknown } }).response !== null
  ) {
    const response = (error as { response?: { data?: unknown } }).response
    const data = response?.data
    const code = getResponseErrorCode(data)
    if (code && ERROR_CODE_MESSAGES[code]) {
      return ERROR_CODE_MESSAGES[code]
    }
    if (
      typeof data === 'object' &&
      data !== null &&
      'detail' in data &&
      typeof (data as { detail?: unknown }).detail === 'object' &&
      (data as { detail?: { message?: unknown } }).detail !== null &&
      typeof (data as { detail?: { message?: unknown } }).detail?.message === 'string'
    ) {
      const message = (data as { detail: { message: string } }).detail.message
      return hasChineseText(message) ? message : fallback
    }
    if (
      typeof data === 'object' &&
      data !== null &&
      'detail' in data &&
      typeof (data as { detail?: unknown }).detail === 'string'
    ) {
      const message = (data as { detail: string }).detail
      return hasChineseText(message) ? message : fallback
    }
  }

  if (
    typeof error === 'object' &&
    error !== null &&
    'message' in error &&
    typeof (error as { message?: unknown }).message === 'string'
  ) {
    const message = (error as { message: string }).message
    return hasChineseText(message) ? message : fallback
  }

  return fallback
}

function getResponseErrorCode(data: unknown): string | null {
  if (typeof data !== 'object' || data === null || !('detail' in data)) {
    return null
  }

  const detail = (data as { detail?: unknown }).detail
  if (typeof detail !== 'object' || detail === null || !('code' in detail)) {
    return null
  }

  const code = (detail as { code?: unknown }).code
  return typeof code === 'string' ? code : null
}

function hasChineseText(value: string): boolean {
  return /[\u4e00-\u9fff]/.test(value)
}
