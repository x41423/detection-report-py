import type { Ref } from 'vue'

import { updateConfig } from '../../api'

export type StatusLogType = 'info' | 'success' | 'error'

export interface StatusLogHandle {
  append(msg: string, type?: StatusLogType): void
  clear(): void
}

export type BrowseMode = 'directory' | 'file'

export interface DirBrowserOpenOptions {
  title?: string
  mode?: BrowseMode
  extensions?: string[]
}

export interface DirBrowserHandle {
  open(initialPath?: string, options?: DirBrowserOpenOptions): Promise<string>
}

export function appendStatus(
  statusLogRef: Ref<StatusLogHandle | undefined>,
  msg: string,
  type: StatusLogType = 'info',
) {
  statusLogRef.value?.append(msg, type)
}

export function clearStatus(statusLogRef: Ref<StatusLogHandle | undefined>) {
  statusLogRef.value?.clear()
}

export async function openPath(
  dirBrowserRef: Ref<DirBrowserHandle | undefined>,
  initialPath: string,
  options: DirBrowserOpenOptions,
) {
  return (await dirBrowserRef.value?.open(initialPath, options)) || ''
}

export async function persistConfig(updates: Record<string, unknown>) {
  await updateConfig(updates)
}
