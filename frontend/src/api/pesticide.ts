import api from './client'
import { toDownloadPayload, type DownloadResponsePayload } from './download'

export interface PesticideTemplateFileInfo {
  configured: boolean
  path: string
  filename: string
  updated_at: string
}

export interface PesticideTemplateStatusResponse {
  big_template: PesticideTemplateFileInfo
  small_template: PesticideTemplateFileInfo
}

export interface MonthlyListEntry {
  date: string
  names: string[]
}

export interface MonthlyListParseError {
  line: number
  message: string
  raw: string
}

export interface MonthlyListParseResponse {
  success: boolean
  entries: MonthlyListEntry[]
  errors: MonthlyListParseError[]
  detected_month?: string
  total_dates: number
  total_names: number
  message: string
}

export function generateRates(vegText: string) {
  return api.post('/api/pesticide/generate-rates', { veg_text: vegText })
}

export function dedupJson(jsonText: string) {
  return api.post('/api/pesticide/dedup-json', { json_text: jsonText })
}

export function formatJson(jsonText: string) {
  return api.post('/api/pesticide/format-json', { json_text: jsonText })
}

export function findFiles(bigDir: string, smallDir: string, year: string, month: string, day: string) {
  return api.post('/api/pesticide/find-files', { big_dir: bigDir, small_dir: smallDir, year, month, day })
}

export function executePesticideTask(params: {
  big_path: string
  small_path: string
  json_text: string
  date_label: string
  output_dir: string
  inspector_name: string
}) {
  return api.post('/api/pesticide/execute', params)
}

export async function executePesticideTaskUpload(params: {
  bigFile: File
  smallFile: File
  jsonText: string
  dateLabel: string
  inspectorName: string
}): Promise<DownloadResponsePayload> {
  const formData = new FormData()
  formData.append('big_file', params.bigFile)
  formData.append('small_file', params.smallFile)
  formData.append('json_text', params.jsonText)
  formData.append('date_label', params.dateLabel)
  formData.append('inspector_name', params.inspectorName)

  const response = await api.post('/api/pesticide/execute/upload', formData, {
    responseType: 'blob',
  })
  return toDownloadPayload(response, 'pesticide-report.zip')
}

export function getPesticideTemplates() {
  return api.get<PesticideTemplateStatusResponse>('/api/pesticide/templates')
}

export function uploadPesticideTemplate(kind: 'big' | 'small', file: File) {
  const formData = new FormData()
  formData.append('template_file', file)
  return api.post<PesticideTemplateStatusResponse>(`/api/pesticide/templates/${kind}`, formData)
}

export function parsePesticideMonthlyList(params: {
  month: string
  listText: string
  listFile?: File | null
}) {
  const formData = new FormData()
  formData.append('month', params.month)
  formData.append('list_text', params.listText || '')
  if (params.listFile) {
    formData.append('list_file', params.listFile)
  }
  return api.post<MonthlyListParseResponse>('/api/pesticide/monthly-list/parse', formData)
}

export async function executePesticideMonthly(params: {
  month: string
  entries: MonthlyListEntry[]
  inspectorName: string
  bigTemplateFile?: File | null
  smallTemplateFile?: File | null
}): Promise<DownloadResponsePayload> {
  const formData = new FormData()
  formData.append('month', params.month)
  formData.append('entries_json', JSON.stringify(params.entries))
  formData.append('inspector_name', params.inspectorName)
  formData.append('use_saved_templates', 'true')
  if (params.bigTemplateFile) {
    formData.append('big_template_file', params.bigTemplateFile)
  }
  if (params.smallTemplateFile) {
    formData.append('small_template_file', params.smallTemplateFile)
  }

  const response = await api.post('/api/pesticide/monthly/execute', formData, {
    responseType: 'blob',
  })
  return toDownloadPayload(response, `农残检测月度报告-${params.month}.zip`)
}

export async function executePesticideMonthlyWithPaths(params: {
  month: string
  entries: MonthlyListEntry[]
  inspectorName: string
  bigTemplatePath: string
  smallTemplatePath: string
  outputDir?: string
}): Promise<DownloadResponsePayload> {
  const formData = new FormData()
  formData.append('month', params.month)
  formData.append('entries_json', JSON.stringify(params.entries))
  formData.append('inspector_name', params.inspectorName)
  formData.append('use_saved_templates', 'false')
  formData.append('big_template_path', params.bigTemplatePath)
  formData.append('small_template_path', params.smallTemplatePath)
  if (params.outputDir) {
    formData.append('output_dir', params.outputDir)
    const response = await api.post<{
      success: boolean
      message: string
      output_dir: string
      generated_files: string[]
      success_count: number
      failure_count: number
    }>('/api/pesticide/monthly/execute', formData)
    return toDownloadPayload(response, `农残检测月度报告-${params.month}.zip`)
  }
  const response = await api.post('/api/pesticide/monthly/execute', formData, {
    responseType: 'blob',
  })
  return toDownloadPayload(response, `农残检测月度报告-${params.month}.zip`)
}
