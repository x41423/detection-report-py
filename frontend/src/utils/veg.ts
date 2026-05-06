export function parseVegNames(text: string): string[] {
  if (!text.trim()) {
    return []
  }

  return text
    .replace(/，/g, ',')
    .replace(/、/g, ',')
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

export function getFileName(path: string): string {
  if (!path) {
    return ''
  }

  return path.split(/[/\\]/).pop() || path
}
