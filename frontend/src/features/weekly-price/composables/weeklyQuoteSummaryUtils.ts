export const WEEKLY_QUOTE_SUPPLIERS = ['勾庄', '理想', '刘慧', '酱菜', '豆制品'] as const

export const WEEKLY_QUOTE_LIMITS: Record<string, number> = {
  勾庄: 7,
  理想: 1,
  刘慧: 1,
  酱菜: 7,
  豆制品: 7,
}

export const WEEKLY_QUOTE_DAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] as const

export interface WeeklyQuoteEntryDraft {
  name: string
  unit: string
  price: number
}

export type WeeklyQuotePasteMode = 'columns' | 'lines' | 'table'

export interface WeeklyQuotePasteForm {
  mode: WeeklyQuotePasteMode
  names: string
  prices: string
  text: string
}

export interface WeeklyQuotePasteResult {
  entries: WeeklyQuoteEntryDraft[]
  pricesOnly: number[]
}

export function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n)
}

export function formatDate(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function parseDate(value: string): Date | null {
  if (!value) return null
  const [y, m, d] = value.split('-').map((part) => Number.parseInt(part, 10))
  if (!y || !m || !d) return null
  const dt = new Date(y, m - 1, d)
  return Number.isNaN(dt.getTime()) ? null : dt
}

export function mondayOf(date: Date): Date {
  const result = new Date(date)
  const day = (result.getDay() + 6) % 7
  result.setDate(result.getDate() - day)
  result.setHours(0, 0, 0, 0)
  return result
}

export function addDays(date: Date, days: number): Date {
  const result = new Date(date)
  result.setDate(result.getDate() + days)
  return result
}

export function getFileName(path: string | null | undefined): string {
  const text = (path || '').toString().trim()
  if (!text) return ''
  const normalized = text.replace(/\\/g, '/')
  const idx = normalized.lastIndexOf('/')
  return idx >= 0 ? normalized.slice(idx + 1) : normalized
}

export function buildEntryId(prefix: string, index: number): string {
  return `${prefix}-${Date.now()}-${index}`
}

export function normalizeEntrySnapshot(entries: WeeklyQuoteEntryDraft[]): string {
  return JSON.stringify(
    entries.map((entry) => ({
      name: entry.name.trim(),
      unit: (entry.unit || '斤').trim(),
      price: Number(entry.price),
    })),
  )
}

export function parseWeeklyQuotePaste(form: WeeklyQuotePasteForm): WeeklyQuotePasteResult {
  if (form.mode === 'columns') {
    return parseColumnPaste(form.names, form.prices)
  }
  if (form.mode === 'table') {
    return parseTablePaste(form.text)
  }
  return parseLinePaste(form.text)
}

function parseColumnPaste(namesText: string, pricesText: string): WeeklyQuotePasteResult {
  const names = splitLines(namesText)
  const prices = splitLines(pricesText).map(parsePrice).filter((price): price is number => price !== null)
  if (!names.length && prices.length) {
    return { entries: [], pricesOnly: prices }
  }

  const entries: WeeklyQuoteEntryDraft[] = []
  const maxLen = Math.max(names.length, prices.length)
  for (let i = 0; i < maxLen; i++) {
    const name = (names[i] || '').trim()
    const price = prices[i]
    if (name && price !== undefined) {
      entries.push({ name, unit: '斤', price })
    }
  }
  return { entries, pricesOnly: [] }
}

function parseLinePaste(text: string): WeeklyQuotePasteResult {
  const entries: WeeklyQuoteEntryDraft[] = []
  const pricesOnly: number[] = []
  for (const line of splitLines(text)) {
    const cells = splitLooseCells(line)
    if (cells.length === 1) {
      const price = parsePrice(cells[0])
      if (price !== null) pricesOnly.push(price)
      continue
    }
    const parsed = inferEntryFromCells(cells)
    if (parsed) entries.push(parsed)
  }
  return { entries, pricesOnly }
}

function parseTablePaste(text: string): WeeklyQuotePasteResult {
  const rows = splitLines(text).map(splitTableCells).filter((row) => row.some(Boolean))
  if (!rows.length) return { entries: [], pricesOnly: [] }

  const headerMap = resolveHeaderMap(rows[0])
  const dataRows = headerMap ? rows.slice(1) : rows
  const entries: WeeklyQuoteEntryDraft[] = []
  const pricesOnly: number[] = []

  for (const row of dataRows) {
    if (headerMap) {
      const name = (row[headerMap.name] || '').trim()
      const unit = headerMap.unit === undefined ? '斤' : (row[headerMap.unit] || '斤').trim() || '斤'
      const price = parsePrice(row[headerMap.price])
      if (name && price !== null) entries.push({ name, unit, price })
      continue
    }

    if (row.length === 1) {
      const price = parsePrice(row[0])
      if (price !== null) pricesOnly.push(price)
      continue
    }
    const parsed = inferEntryFromCells(row)
    if (parsed) entries.push(parsed)
  }

  return { entries, pricesOnly }
}

function resolveHeaderMap(row: string[]): { name: number; unit?: number; price: number } | null {
  let name = -1
  let unit: number | undefined
  let price = -1
  row.forEach((cell, index) => {
    const key = normalizeHeader(cell)
    if (name < 0 && (key.includes('菜名') || key.includes('名称') || key.includes('品名'))) {
      name = index
    }
    if (unit === undefined && key.includes('单位')) {
      unit = index
    }
    if (price < 0 && (key.includes('单价') || key.includes('价格') || key.includes('报价') || key === '价')) {
      price = index
    }
  })
  if (name >= 0 && price >= 0) {
    return { name, unit, price }
  }
  if (name < 0 && price >= 0) {
    return null
  }
  return null
}

function inferEntryFromCells(cells: string[]): WeeklyQuoteEntryDraft | null {
  const clean = cells.map((cell) => cell.trim()).filter(Boolean)
  if (clean.length < 2) return null
  if (clean.length >= 3) {
    const price = parsePrice(clean[2])
    if (clean[0] && clean[1] && price !== null) {
      return { name: clean[0], unit: clean[1], price }
    }
  }
  const price = parsePrice(clean[clean.length - 1])
  if (price === null || !clean[0]) return null
  const maybeUnit = clean.length >= 3 ? clean[clean.length - 2] : '斤'
  return {
    name: clean[0],
    unit: /^[\u4e00-\u9fa5a-zA-Z]+$/.test(maybeUnit) ? maybeUnit : '斤',
    price,
  }
}

function splitLines(text: string): string[] {
  return text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
}

function splitTableCells(line: string): string[] {
  if (line.includes('\t')) {
    return line.split('\t').map((cell) => cell.trim())
  }
  return splitLooseCells(line)
}

function splitLooseCells(line: string): string[] {
  return line.trim().split(/\s+/).map((cell) => cell.trim()).filter(Boolean)
}

function parsePrice(value: unknown): number | null {
  const text = String(value ?? '').trim()
  if (!text) return null
  const parsed = Number.parseFloat(text.replace(/[￥¥元]/g, ''))
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

function normalizeHeader(value: string): string {
  return value.trim().replace(/\s+/g, '').toLowerCase()
}
