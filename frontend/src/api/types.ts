/** Shared API response types — aligns with backend {success, message, items, total} envelope. */

export interface ListResponse<T> {
  success: boolean
  message: string
  items: T[]
  total: number
}

export interface MutationResponse<T = unknown> {
  success: boolean
  message: string
  [key: string]: T | boolean | string | number | undefined
}
