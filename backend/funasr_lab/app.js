const statusStack = document.getElementById('runtime-status')
const statusPill = document.getElementById('status-pill')
const refreshButton = document.getElementById('refresh-status')
const refreshTrackingButton = document.getElementById('refresh-tracking')
const form = document.getElementById('lab-form')
const submitButton = document.getElementById('submit-lab')
const saveTrackingButton = document.getElementById('save-tracking')
const confirmCorrectionButton = document.getElementById('confirm-correction')
const applyLexiconButton = document.getElementById('apply-lexicon')
const exportTrainingPackButton = document.getElementById('export-training-pack')
const saveTrackingHint = document.getElementById('save-tracking-hint')
const lexiconHint = document.getElementById('lexicon-hint')
const resultStack = document.getElementById('result-stack')
const trackingStack = document.getElementById('tracking-stack')
const shadowCompareStack = document.getElementById('shadow-compare-stack')
const fileInput = document.getElementById('audio-file')
const recordStartButton = document.getElementById('record-start')
const recordStopButton = document.getElementById('record-stop')
const audioSource = document.getElementById('audio-source')
const refreshShadowCompareButton = document.getElementById('refresh-shadow-compare')
const exportShadowCompareButton = document.getElementById('export-shadow-compare')

let mediaRecorder = null
let mediaStream = null
let recordedChunks = []
let selectedAudio = null
let lastResultPayload = null

function today() {
  const value = new Date()
  const year = value.getFullYear()
  const month = `${value.getMonth() + 1}`.padStart(2, '0')
  const day = `${value.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

function setStatusPill(kind, text) {
  statusPill.className = `pill ${kind}`
  statusPill.textContent = text
}

function escapeHtml(input) {
  return String(input ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function setAudioSource(file, label) {
  selectedAudio = file
  audioSource.textContent = `${label}: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`
}

function pickSupportedMimeType() {
  if (typeof MediaRecorder === 'undefined' || typeof MediaRecorder.isTypeSupported !== 'function') {
    return ''
  }
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus']
  return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate)) || ''
}

function buildFilenameFromMimeType(mimeType) {
  if (mimeType.includes('mp4')) return 'qwen3-asr-recording.mp4'
  if (mimeType.includes('ogg')) return 'qwen3-asr-recording.ogg'
  return 'qwen3-asr-recording.webm'
}

function renderStatusCards(data) {
  const cards = [
    { title: '运行环境', body: data.message },
    { title: '默认参数', body: JSON.stringify(data.defaults, null, 2) },
    {
      title: '依赖版本',
      body: JSON.stringify(
        {
          qwen_asr: data.qwen_asr_version,
          transformers: data.transformers_version,
          torch: data.torch_version,
        },
        null,
        2,
      ),
    },
  ]

  if (data.memory) {
    cards.push({ title: '运行记忆', body: JSON.stringify(data.memory, null, 2) })
  }

  if (data.lexicon) {
    cards.push({ title: '易错词库', body: JSON.stringify(data.lexicon, null, 2) })
  }

  if (data.tracking) {
    cards.push({ title: '日摄入追踪', body: JSON.stringify(data.tracking, null, 2) })
  }

  statusStack.innerHTML = cards
    .map(
      (card) => `
        <section class="status-card">
          <h3>${card.title}</h3>
          <p>${escapeHtml(card.body)}</p>
        </section>
      `,
    )
    .join('')
}

async function loadStatus() {
  setStatusPill('pill--neutral', '正在检查运行环境')
  try {
    const response = await fetch('/api/test/funasr-lab/status')
    const data = await response.json()
    renderStatusCards(data)
    setStatusPill(
      data.dependency_available ? 'pill--ok' : 'pill--warn',
      data.dependency_available ? 'Qwen3-ASR 可用' : '依赖缺失',
    )
  } catch (error) {
    statusStack.innerHTML = `
      <section class="status-card">
        <h3>状态请求失败</h3>
        <p>${escapeHtml(String(error))}</p>
      </section>
    `
    setStatusPill('pill--danger', '状态检查失败')
  }
}

function currentTrackingDate() {
  return form.elements.intake_date.value || today()
}

function renderTrackingCards(data) {
  const selectedDay = data.selected_day || {
    intake_date: currentTrackingDate(),
    total_count: 0,
    merge_event_count: 0,
    unique_name_count: 0,
    total_quantity: 0,
    items: [],
  }
  const cards = [
    { title: `选中日期 / ${selectedDay.intake_date}`, body: JSON.stringify(selectedDay, null, 2) },
    { title: '最近记录', body: JSON.stringify(data.recent_days || [], null, 2) },
  ]

  trackingStack.innerHTML = cards
    .map(
      (card) => `
        <section class="status-card">
          <h3>${card.title}</h3>
          <p>${escapeHtml(card.body)}</p>
        </section>
      `,
    )
    .join('')
}

async function loadTracking() {
  try {
    const query = new URLSearchParams({
      intake_date: currentTrackingDate(),
      days: '7',
    })
    const response = await fetch(`/api/test/funasr-lab/tracking?${query.toString()}`)
    const data = await response.json()
    renderTrackingCards(data)
  } catch (error) {
    trackingStack.innerHTML = `
      <section class="status-card">
        <h3>日摄入请求失败</h3>
        <p>${escapeHtml(String(error))}</p>
      </section>
    `
  }
}

function renderShadowCompareCards(data) {
  const records = data.records || []
  if (!records.length) {
    shadowCompareStack.innerHTML = `
      <section class="status-card">
        <h3>暂无记录</h3>
        <p>主程序完成语音识别后，会在这里显示 Qwen3-ASR 与 faster-whisper 的 shadow compare 记录。</p>
      </section>
    `
    return
  }

  shadowCompareStack.innerHTML = records
    .slice(0, 20)
    .map((record) => {
      const title = `${record.created_at || 'unknown time'} / final: ${record.final_provider || 'unknown'}`
      const body = JSON.stringify(
        {
          request_id: record.request_id,
          selected_provider: record.selected_provider,
          primary_provider: record.primary_provider,
          backup_provider: record.backup_provider,
          fallback_used: record.fallback_used,
          fallback_reason: record.fallback_reason,
          final_parse_status: record.final_parse_status,
          primary_duration_ms: record.primary_duration_ms,
          backup_duration_ms: record.backup_duration_ms,
          primary_quality_status: record.primary_quality_status,
          backup_quality_status: record.backup_quality_status,
          primary_error: record.primary_error,
          backup_error: record.backup_error,
          primary_transcript: record.primary_transcript,
          backup_transcript: record.backup_transcript,
        },
        null,
        2,
      )
      return `
        <section class="status-card">
          <h3>${escapeHtml(title)}</h3>
          <p>${escapeHtml(body)}</p>
        </section>
      `
    })
    .join('')
}

async function loadShadowCompare() {
  if (!shadowCompareStack) {
    return
  }
  try {
    const response = await fetch('/api/daily-intake/asr-shadow-compare?limit=20')
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || 'shadow compare request failed')
    }
    renderShadowCompareCards(data)
  } catch (error) {
    shadowCompareStack.innerHTML = `
      <section class="status-card">
        <h3>Shadow compare 请求失败</h3>
        <p>${escapeHtml(String(error))}</p>
      </section>
    `
  }
}

function exportShadowCompare() {
  window.location.href = '/api/daily-intake/asr-shadow-compare/export'
}

function getParsedTrackingCandidate(payload) {
  const parsePayload = payload?.daily_intake_parse
  if (!parsePayload || parsePayload.parse_status !== 'parsed') {
    return null
  }
  if (!parsePayload.normalized_name || !parsePayload.unit || !parsePayload.quantity) {
    return null
  }

  return {
    intake_date: currentTrackingDate(),
    raw_name: parsePayload.draft_name || parsePayload.normalized_name,
    normalized_name: parsePayload.normalized_name,
    unit: parsePayload.unit,
    quantity: Number(parsePayload.quantity),
    category: parsePayload.category_hint || form.elements.category.value || null,
    transcript: payload?.asr?.transcript || '',
    source: 'funasr-lab',
  }
}

function syncSaveTrackingState() {
  const candidate = getParsedTrackingCandidate(lastResultPayload)
  if (!candidate) {
    saveTrackingButton.disabled = true
    saveTrackingHint.textContent = '先运行一次可解析的日摄入识别结果。'
    return
  }

  saveTrackingButton.disabled = false
  saveTrackingHint.textContent = `可保存：${candidate.normalized_name} / ${candidate.quantity}${candidate.unit}`
}

function getLexiconCandidate(payload) {
  const entry = payload?.lexicon_candidate?.entry
  if (!entry || !entry.id || !entry.alias || !entry.canonical_name || !entry.unit) {
    return null
  }
  return entry
}

function syncLexiconState() {
  const candidate = getLexiconCandidate(lastResultPayload)
  if (!candidate) {
    confirmCorrectionButton.disabled = true
    lexiconHint.textContent =
      '已确认易错词可应用到下一次 Qwen3-ASR 识别上下文；这不会训练模型权重。'
    return
  }

  confirmCorrectionButton.disabled = candidate.status !== 'pending'
  if (candidate.status === 'pending') {
    lexiconHint.textContent = `待确认易错词：${candidate.alias} -> ${candidate.canonical_name}（${candidate.unit}）`
  } else if (candidate.status === 'confirmed') {
    lexiconHint.textContent = `已确认，待应用：${candidate.alias} -> ${candidate.canonical_name}（${candidate.unit}）`
  } else if (candidate.status === 'active') {
    lexiconHint.textContent = `已生效，正在作为上下文使用：${candidate.alias} -> ${candidate.canonical_name}（${candidate.unit}）`
  } else {
    lexiconHint.textContent = `易错词状态：${candidate.status}`
  }
}

function renderResultCards(data) {
  const cards = [
    { title: `Qwen3-ASR / ${data.asr.model}`, body: data.asr.transcript || '没有返回识别文本。' },
  ]

  if (data.baseline) {
    cards.push({
      title: `正式 STT 对比 / ${data.baseline.provider}`,
      body: data.baseline.error || data.baseline.transcript || '没有正式 STT 对比结果。',
      error: Boolean(data.baseline.error),
    })
  }

  if (data.daily_intake_parse) {
    cards.push({
      title: '日摄入解析',
      body: JSON.stringify(data.daily_intake_parse, null, 2),
    })
  }

  if (data.lexicon_candidate) {
    cards.push({
      title: '易错词候选',
      body: JSON.stringify(data.lexicon_candidate, null, 2),
    })
  }

  cards.push({
    title: '本次配置',
    body: JSON.stringify(data.config, null, 2),
  })

  resultStack.innerHTML = cards
    .map(
      (card) => `
        <section class="result-card ${card.error ? 'result-card--error' : ''}">
          <h3>${card.title}</h3>
          <pre>${escapeHtml(card.body)}</pre>
        </section>
      `,
    )
    .join('')
}

async function submitLab() {
  if (!selectedAudio) {
    alert('请先选择音频文件，或录制一段音频。')
    return
  }

  submitButton.disabled = true
  submitButton.textContent = '识别中...'

  try {
    const formData = new FormData()
    const fields = new FormData(form)
    fields.forEach((value, key) => {
      formData.append(key, value)
    })
    formData.set('compare_with_baseline', String(form.elements.compare_with_baseline.checked))
    formData.set('parse_daily_intake', String(form.elements.parse_daily_intake.checked))
    formData.set('retain_training_audio', String(form.elements.retain_training_audio.checked))
    formData.append('audio', selectedAudio, selectedAudio.name)

    const response = await fetch('/api/test/funasr-lab/transcribe', {
      method: 'POST',
      body: formData,
    })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload.detail || '识别请求失败。')
    }

    lastResultPayload = payload
    renderResultCards(payload)
    syncSaveTrackingState()
    syncLexiconState()
    await Promise.all([loadStatus(), loadTracking(), loadShadowCompare()])
  } catch (error) {
    lastResultPayload = null
    syncSaveTrackingState()
    syncLexiconState()
    resultStack.innerHTML = `
      <section class="result-card result-card--error">
        <h3>ASR 运行失败</h3>
        <pre>${escapeHtml(String(error))}</pre>
      </section>
    `
  } finally {
    submitButton.disabled = false
    submitButton.textContent = '运行 Qwen3-ASR'
  }
}

async function saveTracking() {
  const candidate = getParsedTrackingCandidate(lastResultPayload)
  if (!candidate) {
    syncSaveTrackingState()
    return
  }

  saveTrackingButton.disabled = true
  saveTrackingHint.textContent = '正在保存...'

  try {
    const response = await fetch('/api/test/funasr-lab/tracking/record', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(candidate),
    })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload.detail || '日摄入保存失败。')
    }

    saveTrackingHint.textContent = payload.message || '已保存。'
    await Promise.all([loadStatus(), loadTracking()])
  } catch (error) {
    saveTrackingHint.textContent = `保存失败：${String(error)}`
  } finally {
    syncSaveTrackingState()
  }
}

async function confirmCorrection() {
  const candidate = getLexiconCandidate(lastResultPayload)
  if (!candidate || candidate.status !== 'pending') {
    syncLexiconState()
    return
  }

  confirmCorrectionButton.disabled = true
  lexiconHint.textContent = '正在确认易错词...'

  try {
    const response = await fetch('/api/test/funasr-lab/lexicon/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: [candidate.id] }),
    })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload.detail || '易错词确认失败。')
    }

    candidate.status = 'confirmed'
    confirmCorrectionButton.disabled = true
    lexiconHint.textContent = `${payload.message || '已确认。'} 点击“一键应用增量词库”后，下一次识别会使用它。`
    await loadStatus()
  } catch (error) {
    lexiconHint.textContent = `确认失败：${String(error)}`
    confirmCorrectionButton.disabled = false
  }
}

async function applyIncrementalLexicon() {
  applyLexiconButton.disabled = true
  lexiconHint.textContent = '正在把已确认易错词应用到 ASR 上下文...'

  try {
    const response = await fetch('/api/test/funasr-lab/lexicon/apply-incremental', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope: 'all_confirmed' }),
    })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload.detail || '增量词库应用失败。')
    }

    const candidate = getLexiconCandidate(lastResultPayload)
    if (candidate && candidate.status === 'confirmed' && payload.activated_total > 0) {
      candidate.status = 'active'
    }
    lexiconHint.textContent = `${payload.message} 本次新增生效：${payload.activated_total} 条；当前有效纠错对：${payload.effective_pair_total} 条。`
    await loadStatus()
  } catch (error) {
    lexiconHint.textContent = `应用失败：${String(error)}`
  } finally {
    applyLexiconButton.disabled = false
  }
}

async function exportTrainingPack() {
  exportTrainingPackButton.disabled = true
  lexiconHint.textContent = '正在导出已确认/已生效易错词训练包...'

  try {
    const response = await fetch('/api/test/funasr-lab/lexicon/export-training-pack', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ statuses: ['confirmed', 'active'] }),
    })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload.detail || '训练包导出失败。')
    }

    if (payload.exported_total > 0) {
      lexiconHint.textContent = `已导出 ${payload.exported_total} 条文本纠错到 ${payload.filename}。默认不包含音频绝对路径。`
    } else {
      lexiconHint.textContent = payload.message || '暂无可导出的已确认或已生效易错词。'
    }
    await loadStatus()
  } catch (error) {
    lexiconHint.textContent = `导出失败：${String(error)}`
  } finally {
    exportTrainingPackButton.disabled = false
  }
}

async function startRecording() {
  if (!window.isSecureContext) {
    alert('录音需要 HTTPS 或 localhost 环境。')
    return
  }
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
    alert('当前浏览器不支持在测试页录音。')
    return
  }

  mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  })

  const mimeType = pickSupportedMimeType()
  mediaRecorder = mimeType ? new MediaRecorder(mediaStream, { mimeType }) : new MediaRecorder(mediaStream)
  recordedChunks = []

  mediaRecorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) {
      recordedChunks.push(event.data)
    }
  }

  mediaRecorder.onstop = () => {
    const resolvedMimeType = mediaRecorder?.mimeType || mimeType || 'audio/webm'
    const blob = new Blob(recordedChunks, { type: resolvedMimeType })
    const file = new File([blob], buildFilenameFromMimeType(resolvedMimeType), { type: resolvedMimeType })
    setAudioSource(file, '录音片段')
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop())
    }
    mediaStream = null
    mediaRecorder = null
    recordStartButton.disabled = false
    recordStopButton.disabled = true
  }

  mediaRecorder.start()
  recordStartButton.disabled = true
  recordStopButton.disabled = false
  audioSource.textContent = '正在录音...'
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
}

fileInput.addEventListener('change', () => {
  const [file] = fileInput.files || []
  if (file) {
    setAudioSource(file, '本地文件')
  }
})

form.elements.intake_date.value = today()
form.elements.intake_date.addEventListener('change', () => {
  void loadTracking()
  syncSaveTrackingState()
})

recordStartButton.addEventListener('click', startRecording)
recordStopButton.addEventListener('click', stopRecording)
refreshButton.addEventListener('click', loadStatus)
refreshTrackingButton.addEventListener('click', loadTracking)
refreshShadowCompareButton.addEventListener('click', loadShadowCompare)
exportShadowCompareButton.addEventListener('click', exportShadowCompare)
submitButton.addEventListener('click', submitLab)
saveTrackingButton.addEventListener('click', saveTracking)
confirmCorrectionButton.addEventListener('click', confirmCorrection)
applyLexiconButton.addEventListener('click', applyIncrementalLexicon)
exportTrainingPackButton.addEventListener('click', exportTrainingPack)

syncSaveTrackingState()
syncLexiconState()
loadStatus()
loadTracking()
loadShadowCompare()
