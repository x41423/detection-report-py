<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="980px"
    class="dir-browser"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="dir-browser__toolbar">
      <div class="dir-browser__actions">
        <el-button @click="goUp" :disabled="!canGoUp">返回上一级</el-button>
        <el-button @click="reloadCurrent">刷新</el-button>
      </div>

      <div class="dir-browser__breadcrumb">
        <span class="dir-browser__label">当前位置</span>
        <span class="dir-browser__value">{{ displayPath }}</span>
      </div>
    </div>

    <div class="dir-browser__content">
      <section class="dir-browser__panel">
        <div class="dir-browser__panel-header">
          <span>文件夹</span>
          <span class="soft-note">{{ directories.length }} 项</span>
        </div>

        <div class="dir-browser__list">
          <button
            v-for="dir in directories"
            :key="dir.path"
            type="button"
            class="dir-browser__entry dir-browser__entry--folder"
            @click="openDirectory(dir.path)"
          >
            <div class="dir-browser__entry-icon">目录</div>
            <div class="dir-browser__entry-content">
              <div class="dir-browser__entry-name">{{ dir.name }}</div>
              <div class="dir-browser__entry-path">{{ dir.path }}</div>
            </div>
          </button>

          <div v-if="directories.length === 0" class="dir-browser__empty">
            当前层级没有可进入的文件夹。
          </div>
        </div>
      </section>

      <section v-if="selectMode === 'file'" class="dir-browser__panel">
        <div class="dir-browser__panel-header">
          <span>文件</span>
          <span class="soft-note">{{ filteredFiles.length }} 项</span>
        </div>

        <div class="dir-browser__list">
          <button
            v-for="file in filteredFiles"
            :key="file.path"
            type="button"
            class="dir-browser__entry dir-browser__entry--file"
            :class="{ 'is-active': selectedPath === file.path }"
            @click="selectFile(file.path)"
          >
            <div class="dir-browser__entry-icon">文件</div>
            <div class="dir-browser__entry-content">
              <div class="dir-browser__entry-name">{{ file.name }}</div>
              <div class="dir-browser__entry-path">{{ file.path }}</div>
            </div>
          </button>

          <div v-if="filteredFiles.length === 0" class="dir-browser__empty">
            当前目录下没有符合条件的文件。
          </div>
        </div>
      </section>
    </div>

    <div class="dir-browser__selection">
      <span class="dir-browser__label">已选择</span>
      <span class="dir-browser__value">{{ selectedPath || selectionHint }}</span>
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

type BrowseMode = 'directory' | 'file'

interface OpenOptions {
  title?: string
  mode?: BrowseMode
  extensions?: string[]
}

const LAST_DIRECTORY_KEY = 'dir-browser:last-directory'
const LAST_FILE_KEY = 'dir-browser:last-file'

const visible = ref(false)
const dialogTitle = ref('选择目录')
const currentPath = ref('')
const selectedPath = ref('')
const selectMode = ref<BrowseMode>('directory')
const extensions = ref<string[]>([])

const directories = ref<EntryItem[]>([])
const files = ref<EntryItem[]>([])

let resolveFn: ((path: string) => void) | null = null

const displayPath = computed(() => currentPath.value || '此电脑')
const canGoUp = computed(() => Boolean(currentPath.value))
const selectionHint = computed(() =>
  selectMode.value === 'directory' ? '尚未选择目录' : '尚未选择文件',
)

const filteredFiles = computed(() => {
  if (!extensions.value.length) {
    return files.value
  }
  const normalized = extensions.value.map((ext) => ext.toLowerCase())
  return files.value.filter((file) =>
    normalized.some((ext) => file.name.toLowerCase().endsWith(ext)),
  )
})

async function open(initialPath: string = '', options: OpenOptions = {}): Promise<string> {
  const mode = options.mode || 'directory'
  const fallbackPath = initialPath || loadRememberedPath(mode)
  const parsed = splitInitialPath(fallbackPath)

  dialogTitle.value = options.title || (mode === 'file' ? '选择文件' : '选择目录')
  selectMode.value = mode
  extensions.value = (options.extensions || []).map((ext) => ext.toLowerCase())
  selectedPath.value = mode === 'file' ? parsed.file : parsed.directory
  visible.value = true

  await loadDirectory(parsed.directory)

  return new Promise((resolve) => {
    resolveFn = resolve
  })
}

async function loadDirectory(path: string) {
  try {
    const { data } = await browseDirectory(path)
    currentPath.value = data.path || ''
    directories.value = data.subdirs.map((name: string) => ({
      name: normalizeEntryName(name),
      path: joinWindowsPath(data.path, name),
    }))
    files.value = data.files.map((name: string) => ({
      name,
      path: joinWindowsPath(data.path, name),
    }))

    if (selectMode.value === 'directory') {
      selectedPath.value = currentPath.value
    } else if (selectedPath.value) {
      const hasSelectedFile = files.value.some((file) => file.path === selectedPath.value)
      if (!hasSelectedFile) {
        selectedPath.value = ''
      }
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
  }
}

async function openDirectory(path: string) {
  selectedPath.value = selectMode.value === 'directory' ? path : ''
  await loadDirectory(path)
}

function selectFile(path: string) {
  selectedPath.value = path
}

async function goUp() {
  if (!currentPath.value) {
    return
  }
  await loadDirectory(getParentPath(currentPath.value))
}

async function reloadCurrent() {
  await loadDirectory(currentPath.value)
}

function confirmSelection() {
  const value =
    selectMode.value === 'directory'
      ? currentPath.value || selectedPath.value
      : selectedPath.value

  if (resolveFn) {
    rememberSelection(value || '')
    resolveFn(value || '')
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

function rememberSelection(path: string) {
  if (!path) {
    return
  }

  try {
    if (selectMode.value === 'file') {
      window.localStorage.setItem(LAST_FILE_KEY, path)
      const parsed = splitInitialPath(path)
      if (parsed.directory) {
        window.localStorage.setItem(LAST_DIRECTORY_KEY, parsed.directory)
      }
    } else {
      window.localStorage.setItem(LAST_DIRECTORY_KEY, path)
    }
  } catch {
    // Ignore storage failures.
  }
}

function loadRememberedPath(mode: BrowseMode) {
  try {
    const key = mode === 'file' ? LAST_FILE_KEY : LAST_DIRECTORY_KEY
    return window.localStorage.getItem(key) || ''
  } catch {
    return ''
  }
}

function splitInitialPath(path: string) {
  const trimmed = (path || '').trim()
  if (!trimmed) {
    return { directory: '', file: '' }
  }

  const slashIndex = Math.max(trimmed.lastIndexOf('\\'), trimmed.lastIndexOf('/'))
  const lastPart = slashIndex >= 0 ? trimmed.slice(slashIndex + 1) : trimmed
  const looksLikeFile = /\.[^./\\]+$/.test(lastPart)

  if (!looksLikeFile) {
    return { directory: trimmed, file: '' }
  }

  return {
    directory: slashIndex >= 0 ? trimmed.slice(0, slashIndex) : '',
    file: trimmed,
  }
}

function joinWindowsPath(base: string, child: string) {
  if (!base) {
    return child
  }
  return `${base.replace(/[\\/]$/, '')}\\${child}`
}

function getParentPath(path: string) {
  const normalized = path.replace(/[\\/]$/, '')
  const slashIndex = Math.max(normalized.lastIndexOf('\\'), normalized.lastIndexOf('/'))
  if (slashIndex <= 0) {
    return ''
  }
  return normalized.slice(0, slashIndex)
}

function normalizeEntryName(name: string) {
  return name.endsWith('\\') || name.endsWith('/') ? name.slice(0, -1) : name
}

defineExpose({ open })
</script>

<style scoped>
.dir-browser__toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.dir-browser__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.dir-browser__breadcrumb,
.dir-browser__selection {
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: #fafafa;
  box-shadow: inset 0 0 0 1px rgba(34, 42, 53, 0.08);
}

.dir-browser__breadcrumb {
  min-width: 0;
  flex: 1;
}

.dir-browser__label {
  display: block;
  margin-bottom: 4px;
  color: var(--color-muted-soft);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.dir-browser__value {
  display: block;
  color: var(--color-text);
  line-height: 1.6;
  word-break: break-all;
}

.dir-browser__content {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.dir-browser__panel {
  border-radius: var(--radius-lg);
  background: #ffffff;
  box-shadow: var(--shadow-glass);
  overflow: hidden;
}

.dir-browser__panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  box-shadow: inset 0 -1px 0 rgba(34, 42, 53, 0.08);
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 600;
}

.dir-browser__list {
  max-height: 420px;
  overflow-y: auto;
  padding: 10px;
}

.dir-browser__entry {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  gap: 12px;
  width: 100%;
  padding: 12px 14px;
  margin-bottom: 10px;
  border: 0;
  border-radius: var(--radius-md);
  background: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(34, 42, 53, 0.08);
  cursor: pointer;
  text-align: left;
  transition:
    transform 0.2s ease,
    border-color 0.2s ease,
    background 0.2s ease,
    box-shadow 0.2s ease;
}

.dir-browser__entry:hover {
  transform: translateY(-1px);
  background: #fafafa;
  box-shadow:
    inset 0 0 0 1px rgba(34, 42, 53, 0.12),
    0 2px 6px rgba(17, 17, 17, 0.05);
}

.dir-browser__entry.is-active {
  background: #f7f7f7;
  box-shadow:
    inset 0 0 0 1px rgba(36, 36, 36, 0.4),
    0 2px 6px rgba(17, 17, 17, 0.05);
}

.dir-browser__entry-icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  background: #242424;
  color: #ffffff;
  font-family: var(--font-heading);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.dir-browser__entry--folder .dir-browser__entry-icon {
  background: #242424;
  color: #ffffff;
}

.dir-browser__entry--file .dir-browser__entry-icon {
  background: #f5f5f5;
  color: var(--color-text);
  box-shadow: inset 0 0 0 1px rgba(34, 42, 53, 0.1);
}

.dir-browser__entry-name {
  color: var(--color-text);
  font-size: 14px;
  font-weight: 700;
}

.dir-browser__entry-path {
  margin-top: 4px;
  color: var(--color-muted);
  font-size: 12px;
  line-height: 1.55;
  word-break: break-all;
}

.dir-browser__empty {
  padding: 32px 18px;
  color: var(--color-muted);
  text-align: center;
}

.dir-browser__selection {
  margin-top: 16px;
}

@media (max-width: 900px) {
  .dir-browser__toolbar {
    display: grid;
  }

  .dir-browser__content {
    grid-template-columns: 1fr;
  }
}
</style>
