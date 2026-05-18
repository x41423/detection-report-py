import api from './client'

export interface AuthUser {
  id: number
  username: string
  display_name: string
  roles: string[]
  permissions: string[]
  is_super_admin: boolean
  must_change_password: boolean
  is_active: boolean
}

export interface AuthTokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_at: string
  user: AuthUser
}

export interface AuthPendingLoginResponse {
  requires_device_replacement: true
  pending_token: string
  expires_at: string
  max_devices: number
  devices: AuthDevice[]
  message: string
}

export type AuthLoginResult = AuthTokenResponse | AuthPendingLoginResponse

export interface AuthRegisterResponse {
  success: boolean
  message: string
  user: AuthUser
}

export interface AuthMeResponse {
  user: AuthUser
}

export interface AuthLogoutResponse {
  success: boolean
  message: string
}

export interface AuthDevice {
  id: number
  device_name: string
  user_agent: string
  ip_address: string
  first_login_at: string
  last_active_at: string
  is_revoked: boolean
  revoked_at: string | null
  active_session_count: number
  is_current: boolean
}

export interface AuthDeviceListResponse {
  devices: AuthDevice[]
  total: number
}

export interface AuthDeviceMutationResponse {
  success: boolean
  message: string
  device: AuthDevice
}

export interface AuthPermission {
  code: string
  name: string
  module: string
  description: string
  has_permission: boolean
}

export interface AuthPermissionCatalogResponse {
  permissions: AuthPermission[]
}

export interface AuthPermissionRequest {
  id: number
  user_id: number
  username: string
  display_name: string
  permission_code: string
  permission_name: string
  permission_module: string
  reason: string
  status: 'pending' | 'approved' | 'rejected' | 'cancelled'
  reviewer_id: number | null
  reviewer_username: string | null
  reviewer_display_name: string | null
  review_comment: string
  created_at: string
  reviewed_at: string | null
}

export interface AuthPermissionRequestListResponse {
  requests: AuthPermissionRequest[]
  total: number
}

export interface AuthPermissionRequestMutationResponse {
  success: boolean
  message: string
  request: AuthPermissionRequest
}

export interface AuthManagedUser {
  id: number
  username: string
  display_name: string
  roles: string[]
  permissions: string[]
  is_active: boolean
  is_super_admin: boolean
  must_change_password: boolean
  last_login_at: string | null
  created_at: string
  active_session_count: number
}

export interface AuthManagedUserListResponse {
  users: AuthManagedUser[]
  total: number
}

export interface AuthManagedUserMutationResponse {
  success: boolean
  message: string
  user: AuthManagedUser
}

export interface AuthManagedUserDeleteResponse {
  success: boolean
  message: string
}

export interface AuthRole {
  id: number
  code: string
  name: string
  description: string
  is_system: boolean
  permission_codes: string[]
  user_count: number
  created_at: string
  updated_at: string
}

export interface AuthRoleListResponse {
  roles: AuthRole[]
  total: number
}

export interface AuthRoleMutationResponse {
  success: boolean
  message: string
  role: AuthRole
}

export interface AuthAuditLog {
  id: number
  actor_user_id: number | null
  actor_username: string | null
  actor_display_name: string | null
  target_user_id: number | null
  target_username: string | null
  target_display_name: string | null
  action: string
  module: string
  description: string
  ip_address: string
  user_agent: string
  result: 'success' | 'failure' | 'pending'
  created_at: string
}

export interface AuthAuditLogListResponse {
  logs: AuthAuditLog[]
  total: number
}

export interface LoginPayload {
  username: string
  password: string
  device_name?: string
}

export interface RegisterPayload {
  username: string
  password: string
  display_name?: string
}

export interface RenameDevicePayload {
  device_name: string
}

export interface ReplaceDeviceLoginPayload {
  pending_token: string
  replace_device_id: number
}

export interface CreatePermissionRequestPayload {
  permission_code: string
  reason: string
}

export interface ReviewPermissionRequestPayload {
  status: 'approved' | 'rejected'
  review_comment: string
}

export interface CreateManagedUserPayload {
  username: string
  password: string
  display_name?: string
  role_codes: string[]
}

export interface UpdateManagedUserPayload {
  display_name?: string
  role_codes?: string[]
  is_active?: boolean
}

export interface CreateRolePayload {
  code: string
  name: string
  description: string
  permission_codes: string[]
}

export interface UpdateRolePayload {
  name: string
  description: string
  permission_codes: string[]
}

export interface AuditLogFilters {
  limit?: number
  module?: string
  action?: string
  result?: AuthAuditLog['result'] | ''
  actor_user_id?: number
  target_user_id?: number
}

export function login(payload: LoginPayload) {
  return api.post<AuthLoginResult>('/api/auth/login', payload, { withCredentials: true })
}

export function register(payload: RegisterPayload) {
  return api.post<AuthRegisterResponse>('/api/auth/register', payload, { withCredentials: true })
}

export function refreshSession() {
  return api.post<AuthTokenResponse>('/api/auth/refresh', undefined, { withCredentials: true })
}

export function getCurrentUser() {
  return api.get<AuthMeResponse>('/api/auth/me')
}

export function logout() {
  return api.post<AuthLogoutResponse>('/api/auth/logout', undefined, { withCredentials: true })
}

export function listDevices() {
  return api.get<AuthDeviceListResponse>('/api/auth/devices')
}

export function renameDevice(deviceId: number, payload: RenameDevicePayload) {
  return api.put<AuthDeviceMutationResponse>(`/api/auth/devices/${deviceId}`, payload)
}

export function revokeDevice(deviceId: number) {
  return api.delete<AuthDeviceMutationResponse>(`/api/auth/devices/${deviceId}`, { withCredentials: true })
}

export function replaceDeviceLogin(payload: ReplaceDeviceLoginPayload) {
  return api.post<AuthTokenResponse>('/api/auth/device-replacement', payload, { withCredentials: true })
}

export function isPendingLoginResponse(payload: AuthLoginResult): payload is AuthPendingLoginResponse {
  return 'requires_device_replacement' in payload && payload.requires_device_replacement === true
}

export function listPermissions() {
  return api.get<AuthPermissionCatalogResponse>('/api/auth/permissions')
}

export function createPermissionRequest(payload: CreatePermissionRequestPayload) {
  return api.post<AuthPermissionRequestMutationResponse>('/api/auth/permission-requests', payload)
}

export function listMyPermissionRequests() {
  return api.get<AuthPermissionRequestListResponse>('/api/auth/permission-requests/mine')
}

export function listPermissionRequests(status?: AuthPermissionRequest['status'] | '') {
  return api.get<AuthPermissionRequestListResponse>('/api/auth/permission-requests', {
    params: status ? { status } : undefined,
  })
}

export function reviewPermissionRequest(requestId: number, payload: ReviewPermissionRequestPayload) {
  return api.post<AuthPermissionRequestMutationResponse>(`/api/auth/permission-requests/${requestId}/review`, payload)
}

export function listManagedUsers() {
  return api.get<AuthManagedUserListResponse>('/api/auth/users')
}

export function createManagedUser(payload: CreateManagedUserPayload) {
  return api.post<AuthManagedUserMutationResponse>('/api/auth/users', payload)
}

export function updateManagedUser(userId: number, payload: UpdateManagedUserPayload) {
  return api.patch<AuthManagedUserMutationResponse>(`/api/auth/users/${userId}`, payload)
}

export function deleteManagedUser(userId: number) {
  return api.delete<AuthManagedUserDeleteResponse>(`/api/auth/users/${userId}`)
}

export function listRoles() {
  return api.get<AuthRoleListResponse>('/api/auth/roles')
}

export function createRole(payload: CreateRolePayload) {
  return api.post<AuthRoleMutationResponse>('/api/auth/roles', payload)
}

export function updateRole(roleId: number, payload: UpdateRolePayload) {
  return api.put<AuthRoleMutationResponse>(`/api/auth/roles/${roleId}`, payload)
}

export function deleteRole(roleId: number) {
  return api.delete<{ success: boolean; message: string }>(`/api/auth/roles/${roleId}`)
}

export function listAuditLogs(filters: AuditLogFilters = {}) {
  return api.get<AuthAuditLogListResponse>('/api/auth/audit-logs', {
    params: filters,
  })
}
