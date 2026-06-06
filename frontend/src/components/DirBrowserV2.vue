<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="980px"
    class="dir-browser-v2"
    :close-on-click-modal="false"
    append-to-body
    @close="handleClose"
  >
    <!-- 导航栏：面包屑 + 地址栏 + 操作按钮 -->
    <div class="dir-browser-v2__toolbar">
      <div class="dir-browser-v2__nav-row">
        <el-button-group class="dir-browser-v2__nav-btns">
          <el-button :disabled="!canGoForward" @click="goForward" title="前进">
            <span class="arrow">▶</span>
          </el-button>
          <el-button :disabled="!canGoBack" @click="goBack" title="后退">
            <span class="arrow">◀</span>
          </el-button>
        </el-button-group>

        <div class="dir-browser-v2__address-bar">
          <span
            v-for="(segment, idx) in breadcrumbSegments"
            :key="idx"
            class="dir-browser-v2__crumb"
            @click="goToBreadcrumb(idx)"
          >
            <span v-if="idx > 0" class="dir-browser-v2__crumb-sep">\</span>
            <span class="dir-browser-v2__crumb-text">{{ segment.label }}</span>
          </span>
        </div>

        <div class="dir-browser-v2__drive-dropdown">
          <el-dropdown @command="onDriveSelect">
            <el-button size="small">
              盘符
              <el-icon class="el-icon--right"><span>▾</span></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-for="drive in drives"
                  :key="drive"
                  :command="drive"
                >
                  {{ drive }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <el-button size="small" @click="reloadCurrent" :loading="loading">刷新</el-button>
      </div>

      <!-- 搜索 + 过滤 -->
      <div class="dir-browser-v2__filter-row">
        <el-input
          v-model="nameFilter"
          placeholder="搜索文件名..."
          size="small"
          clearable
          class="dir-browser-v2__search"
        />
        <el-switch
          v-model="showHidden"
          size="small"
          active-text="显示隐藏"
          inactive-text="隐藏隐藏"
        />
      </div>
    </div>

    <!-- 内容区 -->
    <div class="dir-browser-v2__content">
      <section class="dir-browser-v2__panel">
        <div class="dir-browser-v2__panel-header">
          <span>文件夹</span>
          <span class="soft-note">{{ displayedDirs.length }} 项</span>
        </div>
        <div class="dir-browser-v2__list">
          <button
            v-for="dir in displayedDirs"
            :key="dir.path"
            type="button"
            class="dir-browser-v2__entry dir-browser-v2__entry--folder"
            @click="openDirectory(dir.path)"
          >
            <div class="dir-browser-v2__entry-icon">📁</div>
            <div class="dir-browser-v2__entry-content">
              <div class="dir-browser-v2__entry-name">{{ dir.name }}</div>
              <div class="dir-browser-v2__entry-path">{{ dir.path }}</div>
            </div>
          </button>
          <div v-if="displayedDirs.length === 0" class="dir-browser-v2__empty">
            当前层级没有可进入的文件夹。
          </div>
        </div>
      </section>

      <section v-if="selectMode === 'file' || selectMode === 'multi-file'" class="dir-browser-v2__panel">
        <div class="dir-browser-v2__panel-header">
          <span>文件</span>
          <span class="soft-note">{{ displayedFiles.length }} 项</span>
        </div>
        <div class="dir-browser-v2__list">
          <button
            v-for="file in displayedFiles"
            :key="file.path"
            type="button"
            class="dir-browser-v2__entry dir-browser-v2__entry--file"
            :class="{
              'is-active': selectMode === 'multi-file'
                ? selectedPaths.includes(file.path)
                : selectedPath === file.path,
            }"
            @click="selectMode === 'multi-file' ? toggleMultiSelect(file.path) : selectFile(file.path)"
          >
            <div class="dir-browser-v2__entry-icon">📄</div>
            <div class="dir-browser-v2__entry-content">
              <div class="dir-browser-v2__entry-name">{{ file.name }}</div>
              <div class="dir-browser-v2__entry-path">{{ file.path }}</div>
            </div>
          </button>
          <div v-if="displayedFiles.length === 0" class="dir-browser-v2__empty">
            当前目录下没有符合条件的文件。
          </div>
        </div>
      </section>
    </div>

    <!-- 选择区 -->
    <div class="dir-browser-v2__selection">
      <span class="dir-browser-v2__label">已选择</span>
      <span class="dir-browser-v2__value">
        {{ selectMode === 'multi-file' ? selectedPaths.join('; ') || selectionHint : selectedPath || selectionHint }}
      </span>
    </div>

    <!-- 保存为输入 -->
    <div v-if="selectMode === 'save-as'" class="dir-browser-v2__saveas">
      <el-input
        v-model="saveAsName"
        placeholder="输入文件名（如：模板_2026.xlsx）"
        size="default"
      />
    </div>

    <template #footer>
      <el-button @click="cancel">取消</el-button>
      <el-button type="primary" @click="confirmSelection">确认选择</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { browseDirectory } from '../api'

interface EntryItem {
  name: string
  path: string
}

export type BrowseMode = 'directory' | 'file' | 'multi-file' | 'save-as'

export interface DirBrowserV2OpenOptions {
  title?: string
  mode?: BrowseMode
  extensions?: string[]
  scope?: string
  remember?: boolean
}

const SCOPE_PREFIX = 'dir-browser-v2:scope:'
const GLOBAL_DEFAULT_DIR = 'dir-browser-v2:default-dir'

const visible = ref(false)
const dialogTitle = ref('选择目录')
const currentPath = ref('')
const selectedPath = ref('')
const selectedPaths = ref<string[]>([])
const selectMode = ref<BrowseMode>('directory')
const extensions = ref<string[]>([])
const saveAsName = ref('')
const currentScope = ref('')
const shouldRemember = ref(true)
const loading = ref(false)

const directories = ref<EntryItem[]>([])
const files = ref<EntryItem[]>([])
const drives = ref<string[]>(['C:', 'D:', 'E:', 'F:', 'G:'])

// 导航历史
const navHistory = ref<string[]>([])
const navIndex = ref(-1)

// 过滤
const nameFilter = ref('')
const showHidden = ref(false)

let resolveFn: ((path: string | string[]) => void) | null = null

const displayPath = computed(() => currentPath.value || '此电脑')

const breadcrumbSegments = computed(() => {
  if (!currentPath.value) return [{ label: '此电脑', path: '' }]
  const parts = currentPath.value.split('\\').filter(Boolean)
  let accumulated = ''
  return parts.map((part) => {
    accumulated = accumulated ? accumulated + '\\' + part : part
    return { label: part, path: accumulated }
  })
})

const canGoBack = computed(() => navIndex.value > 0)
const canGoForward = computed(() => navIndex.value < navHistory.value.length - 1)

const selectionHint = computed(() => {
  switch (selectMode.value) {
    case 'directory': return '当前目录即为选中目录'
    case 'multi-file': return '点击文件多选（尚未选择）'
    default: return '尚未选择文件'
  }
})

const displayedDirs = computed(() => {
  if (!nameFilter.value.trim() && !showHidden.value) return directories.value
  let result = directories.value
  if (!showHidden.value) result = result.filter(d => !d.name.startsWith('.') && !d.name.startsWith('$'))
  if (nameFilter.value.trim()) {
    const q = nameFilter.value.toLowerCase()
    result = result.filter(d => d.name.toLowerCase().includes(q))
  }
  return result
})

const displayedFiles = computed(() => {
  let result = files.value
  if (!showHidden.value) result = result.filter(f => !f.name.startsWith('.') && !f.name.startsWith('$'))
  if (nameFilter.value.trim()) {
    const q = nameFilter.value.toLowerCase()
    result = result.filter(f => f.name.toLowerCase().includes(q))
  }
  if (extensions.value.length) {
    const normalized = extensions.value.map(e => e.toLowerCase())
    result = result.filter(f => normalized.some(e => f.name.toLowerCase().endsWith(e)))
  }
  return result
})

async function open(
  initialPath: string = '',
  options: DirBrowserV2OpenOptions = {},
): Promise<string | string[]> {
  const mode = options.mode || 'directory'

  currentScope.value = options.scope || ''
  shouldRemember.value = options.remember !== false

  const fallbackPath = initialPath || loadScopePath(mode)
  const parsed = splitInitialPath(fallbackPath)

  dialogTitle.value = options.title || getDefaultTitle(mode)
  selectMode.value = mode
  extensions.value = (options.extensions || []).map(e => e.toLowerCase())
  selectedPath.value = mode === 'file' || mode === 'save-as' ? parsed.file : parsed.directory
  selectedPaths.value = []
  saveAsName.value = ''
  nameFilter.value = ''
  visible.value = true

  // 初始化导航历史
  navHistory.value = [parsed.directory || '']
  navIndex.value = 0

  await loadDirectory(parsed.directory)

  return new Promise((resolve) => {
    resolveFn = resolve
  })
}

// Use default drives (no backend endpoint needed)

async function loadDirectory(path: string) {
  loading.value = true
  try {
    const { data } = await browseDirectory(path)
    currentPath.value = data.path || ''
    directories.value = (data.subdirs || []).map((name: string) => ({
      name: normalizeEntryName(name),
      path: joinWindowsPath(data.path, name),
    }))
    files.value = (data.files || []).map((name: string) => ({
      name,
      path: joinWindowsPath(data.path, name),
    }))

    if (selectMode.value === 'directory') {
      selectedPath.value = currentPath.value
    }
  } catch {
    if (path) {
      await loadDirectory('')
      return
    }
    currentPath.value = ''
    directories.value = []
    files.value = []
    selectedPath.value = ''
  } finally {
    loading.value = false
  }
}

function navigateTo(path: string) {
  // 丢弃当前位置之后的历史
  navHistory.value = navHistory.value.slice(0, navIndex.value + 1)
  navHistory.value.push(path)
  navIndex.value = navHistory.value.length - 1
}

async function openDirectory(path: string) {
  selectedPath.value = selectMode.value === 'directory' ? path : ''
  navigateTo(path)
  await loadDirectory(path)
}

function selectFile(path: string) {
  selectedPath.value = path
}

function toggleMultiSelect(path: string) {
  const idx = selectedPaths.value.indexOf(path)
  if (idx >= 0) {
    selectedPaths.value.splice(idx, 1)
  } else {
    selectedPaths.value.push(path)
  }
}

async function goBack() {
  if (canGoBack.value) {
    navIndex.value--
    await loadDirectory(navHistory.value[navIndex.value])
  }
}

async function goForward() {
  if (canGoForward.value) {
    navIndex.value++
    await loadDirectory(navHistory.value[navIndex.value])
  }
}

async function goToBreadcrumb(idx: number) {
  const path = breadcrumbSegments.value[idx].path
  if (path === currentPath.value) return
  navigateTo(path)
  await loadDirectory(path)
}

function onDriveSelect(drive: string) {
  navigateTo(drive)
  loadDirectory(drive)
}

async function reloadCurrent() {
  await loadDirectory(currentPath.value)
}

function confirmSelection() {
  let value: string | string[] = ''

  if (selectMode.value === 'multi-file') {
    value = [...selectedPaths.value]
  } else if (selectMode.value === 'directory') {
    value = currentPath.value || selectedPath.value
  } else if (selectMode.value === 'save-as') {
    const dir = currentPath.value || ''
    const name = saveAsName.value.trim()
    value = name ? joinWindowsPath(dir, name) : dir
  } else {
    value = selectedPath.value
  }

  if (resolveFn) {
    if (shouldRemember.value && value) {
      rememberScopePath(value, selectMode.value)
    }
    resolveFn(value)
    resolveFn = null
  }
  visible.value = false
}

function cancel() {
  if (resolveFn) {
    resolveFn('')
    resolveFn = null
  }
  visible.value = false
}

function handleClose() {
  if (resolveFn) {
    resolveFn('')
    resolveFn = null
  }
}

function getScopeKey(mode: BrowseMode): string {
  const scope = currentScope.value || '__default__'
  return `${SCOPE_PREFIX}${scope}:${mode}`
}

function loadScopePath(mode: BrowseMode): string {
  try {
    return window.localStorage.getItem(getScopeKey(mode)) || ''
  } catch {
    return ''
  }
}

function rememberScopePath(path: string | string[], mode: BrowseMode) {
  if (!path || (Array.isArray(path) && path.length === 0)) return
  try {
    const stored = Array.isArray(path) ? path[0] : path
    // Store for this specific scope+mode
    window.localStorage.setItem(getScopeKey(mode), stored)
    // Also extract directory part if it's a file mode
    if (mode === 'file' || mode === 'multi-file' || mode === 'save-as') {
      const parsed = splitInitialPath(stored)
      if (parsed.directory) {
        window.localStorage.setItem(getScopeKey('directory'), parsed.directory)
      }
    }
  } catch {
    // Ignore
  }
}

function getDefaultTitle(mode: BrowseMode): string {
  switch (mode) {
    case 'file': return '选择文件'
    case 'multi-file': return '选择多个文件'
    case 'save-as': return '另存为'
    default: return '选择目录'
  }
}

// --- Utils (same as v1) ---
function splitInitialPath(path: string) {
  const trimmed = (path || '').trim()
  if (!trimmed) return { directory: '', file: '' }
  const slashIndex = Math.max(trimmed.lastIndexOf('\\'), trimmed.lastIndexOf('/'))
  const lastPart = slashIndex >= 0 ? trimmed.slice(slashIndex + 1) : trimmed
  const looksLikeFile = /\.[^./\\]+$/.test(lastPart)
  if (!looksLikeFile) return { directory: trimmed, file: '' }
  return { directory: slashIndex >= 0 ? trimmed.slice(0, slashIndex) : '', file: trimmed }
}

function joinWindowsPath(base: string, child: string) {
  if (!base) return child
  return `${base.replace(/[\\/]$/, '')}\\${child}`
}

function normalizeEntryName(name: string) {
  return name.endsWith('\\') || name.endsWith('/') ? name.slice(0, -1) : name
}

defineExpose({ open })
</script>

<style scoped>
.dir-browser-v2__toolbar {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dir-browser-v2__nav-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.dir-browser-v2__nav-btns .arrow {
  font-size: 10px;
}

.dir-browser-v2__address-bar {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-card);
  overflow-x: auto;
  white-space: nowrap;
  font-size: 13px;
}

.dir-browser-v2__crumb {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  border-radius: 3px;
  padding: 2px 4px;
  transition: background 0.15s;
}

.dir-browser-v2__crumb:hover {
  background: var(--color-primary-soft);
}

.dir-browser-v2__crumb-sep {
  color: var(--color-muted-soft);
  margin: 0 2px;
}

.dir-browser-v2__crumb-text {
  color: var(--color-text);
}

.dir-browser-v2__filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dir-browser-v2__search {
  max-width: 280px;
}

.dir-browser-v2__content {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.dir-browser-v2__panel {
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.dir-browser-v2__panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 600;
}

.dir-browser-v2__list {
  max-height: 380px;
  overflow-y: auto;
  padding: 10px;
}

.dir-browser-v2__entry {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr);
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  margin-bottom: 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.18s ease, background 0.18s ease;
}

.dir-browser-v2__entry:hover {
  border-color: var(--color-border-highlight);
  background: var(--color-surface-card);
}

.dir-browser-v2__entry.is-active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.dir-browser-v2__entry-icon {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  font-size: 18px;
}

.dir-browser-v2__entry--folder .dir-browser-v2__entry-icon {
  background: var(--color-surface-card);
}

.dir-browser-v2__entry--file .dir-browser-v2__entry-icon {
  background: var(--color-surface-card);
}

.dir-browser-v2__entry-name {
  color: var(--color-text);
  font-size: 14px;
  font-weight: 600;
}

.dir-browser-v2__entry-path {
  margin-top: 3px;
  color: var(--color-muted);
  font-size: 11px;
  line-height: 1.5;
  word-break: break-all;
}

.dir-browser-v2__empty {
  padding: 32px 18px;
  color: var(--color-muted);
  text-align: center;
}

.dir-browser-v2__selection {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: var(--color-surface-card);
}

.dir-browser-v2__selection .dir-browser-v2__label {
  display: block;
  margin-bottom: 4px;
  color: var(--color-muted-soft);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.dir-browser-v2__selection .dir-browser-v2__value {
  display: block;
  color: var(--color-text);
  line-height: 1.6;
  word-break: break-all;
}

.dir-browser-v2__saveas {
  margin-top: 12px;
}

@media (max-width: 900px) {
  .dir-browser-v2__content {
    grid-template-columns: 1fr;
  }
}
</style>
