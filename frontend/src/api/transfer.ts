import api from './client'
import { toDownloadPayload, type DownloadResponsePayload } from './download'

export interface TransferDetectResponse {
  success: boolean
  message: string
  varieties: string[]
  count: number
}

export interface TransferDedupResponse {
  success: boolean
  message: string
  deduplicated: string[]
  removed_count: number
}

export interface TransferTemplateInfo {
  configured: boolean
  path: string
  filename: string
  updated_at: string
}

export interface TransferTemplateStatusResponse {
  templates: Record<string, TransferTemplateInfo>
}

export interface MonthlyTransferGroup {
  date: string
  files: string[]
  count: number
}

export interface MonthlyTransferPreviewResponse {
  success: boolean
  groups: MonthlyTransferGroup[]
  unrecognized_files: string[]
  total_files: number
  message: string
}

/**
 * Detect varieties contained in a batch of "big table" Excel files.  The
 * server scans the upload payloads and returns a deduplicated, sorted list of
 * variety names so the user can confirm before kicking off the migration.
 */
export function extractVarietiesFromUploads(files: File[] | FileList) {
  const formData = new FormData()
  Array.from(files).forEach((file) => {
    formData.append('files', file)
  })
  return api.post<TransferDetectResponse>('/api/transfer/varieties/upload', formData)
}

/**
 * Server-side deduplication for a comma/whitespace-separated list of veg
 * names.  Used by the transfer page so the user can paste a long list and
 * collapse duplicates before submitting.
 */
export function dedupVegNames(names: string[]) {
  return api.post<TransferDedupResponse>('/api/transfer/dedup', { veg_names: names })
}

/**
 * Inspect the persisted small-table templates that the backend keeps on the
 * filesystem.  Returns one entry per supported small-type kind.
 */
export function getTransferTemplates() {
  return api.get<TransferTemplateStatusResponse>('/api/transfer/templates')
}

/**
 * Upload a small-table template for one of the supported kinds (滨鲜 / 1号 / ...).
 */
export function uploadTransferTemplateFile(kind: string, file: File) {
  const formData = new FormData()
  formData.append('kind', kind)
  formData.append('template_file', file)
  return api.post<TransferTemplateStatusResponse>('/api/transfer/templates/upload', formData)
}

/**
 * Group a folder of "monthly" Excel uploads by date so the user can preview
 * which files will be processed before launching the long-running migration.
 */
export function previewMonthlyTransferUpload(params: { files: File[]; month: string }) {
  const formData = new FormData()
  params.files.forEach((file) => {
    formData.append('files', file)
  })
  formData.append('month', params.month)
  return api.post<MonthlyTransferPreviewResponse>('/api/transfer/monthly/preview', formData)
}

/**
 * Run the full transfer workflow against a batch of uploads.  The backend
 * streams the result file back and includes counters in the response headers.
 */
export async function executeTransferUpload(params: {
  tableFiles: File[]
  smallTemplate: File | null
  vegNames: string[]
  smallType: string
}): Promise<DownloadResponsePayload> {
  const formData = new FormData()
  params.tableFiles.forEach((file) => {
    formData.append('table_files', file)
  })
  if (params.smallTemplate) {
    formData.append('small_template_file', params.smallTemplate)
  }
  formData.append('veg_names_json', JSON.stringify(params.vegNames))
  formData.append('small_type', params.smallType)
  const response = await api.post('/api/transfer/execute/upload', formData, {
    responseType: 'blob',
  })
  return toDownloadPayload(response, 'transfer-result.xlsx')
}

/**
 * Run the monthly transfer workflow.  The server zips up the per-day results
 * and streams a single download back.
 */
export async function executeMonthlyTransferUpload(params: {
  files: File[]
  month: string
  smallType: string
  smallTemplate: File | null
}): Promise<DownloadResponsePayload> {
  const formData = new FormData()
  params.files.forEach((file) => {
    formData.append('files', file)
  })
  formData.append('month', params.month)
  formData.append('small_type', params.smallType)
  if (params.smallTemplate) {
    formData.append('small_template_file', params.smallTemplate)
  }
  const response = await api.post('/api/transfer/monthly/execute', formData, {
    responseType: 'blob',
  })
  return toDownloadPayload(response, `monthly-transfer-${params.month}.zip`)
}

/**
 * Browse a server-side directory.  Used by the directory picker dialog on the
 * data transfer page.
 */
export function browseTransferDirectory(path: string) {
  return api.get<{
    path: string
    parent: string | null
    items: { name: string; path: string; is_dir: boolean }[]
  }>('/api/transfer/browse', { params: { path } })
}

export interface BrowseDirectoryResponse {
  path: string
  subdirs: string[]
  files: string[]
}

export function browseDirectory(path: string) {
  return api.post<BrowseDirectoryResponse>('/api/transfer/browse', { path })
}

/**
 * Notify the backend when path-lock state is restored from localStorage cache,
 * so the server operator can see the event in the log / CMD window.
 */
export function logPathRestore(bigDir: string) {
  return api.post('/api/transfer/log-restore', { path: bigDir }).catch(() => {})
}

/**
 * Find .doc/.docx files in a server-side directory for path-locking mode.
 */
export function findTransferFiles(dir: string) {
  return api.post<BrowseDirectoryResponse>('/api/transfer/find-files', { path: dir })
}

export interface TransferVarietiesResponse {
  varieties: string[]
  count: number
}

/**
 * Extract varieties from server-side file paths (not uploads).
 */
export function extractVarietiesFromPaths(tablePaths: string[]) {
  return api.post<TransferVarietiesResponse>('/api/transfer/varieties', { table_paths: tablePaths })
}

/**
 * Execute a single transfer using server-side file paths, returns download blob.
 * When outputDir is provided the file is saved directly to that directory on the
 * server and a JSON response is returned instead of a blob.
 */
export async function executeTransferFromPaths(params: {
  tablePaths: string[]
  smallTemplatePath: string
  vegNames: string[]
  smallType: string
  outputDir?: string
}): Promise<DownloadResponsePayload> {
  const formData = new FormData()
  formData.append('table_paths_json', JSON.stringify(params.tablePaths))
  formData.append('small_template_path', params.smallTemplatePath)
  formData.append('veg_names_json', JSON.stringify(params.vegNames))
  formData.append('small_type', params.smallType)
  if (params.outputDir) {
    formData.append('output_dir', params.outputDir)
    const response = await api.post<{
      success: boolean
      message: string
      output_file: string
      processed_files: number
      matched_count: number
      written_count: number
    }>('/api/transfer/execute-from-paths', formData)
    return toDownloadPayload(response, 'transfer-result.docx')
  }
  const response = await api.post('/api/transfer/execute-from-paths', formData, {
    responseType: 'blob',
  })
  return toDownloadPayload(response, 'transfer-result.docx')
}
