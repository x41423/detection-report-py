import { onBeforeUnmount, ref, type Ref } from 'vue'

import type { DailyIntakeSpeechState } from '../types'

interface RecordedAudioPayload {
  blob: Blob
  filename: string
  mimeType: string
}

interface MediaRecorderErrorEventLike extends Event {
  error?: DOMException
}

function getCurrentOrigin() {
  if (typeof location === 'undefined') {
    return ''
  }
  return location.origin || `${location.protocol}//${location.host}`
}

function buildInsecureContextMessage() {
  const origin = getCurrentOrigin()
  const originText = origin ? `当前地址 ${origin}` : '当前页面'
  return `${originText} 不是安全上下文，手机 Chrome 下不会弹出麦克风授权。请改用 HTTPS 地址打开，或改在本机 localhost 环境下使用录音。`
}

function buildPermissionDeniedMessage() {
  return '浏览器未授予麦克风权限，请在地址栏的网站权限设置里允许麦克风后重试。'
}

function buildRecorderUnavailableMessage() {
  return '当前浏览器不支持本地录音上传，请改用较新的 Chrome、Safari 或 Edge。'
}

function buildRecorderStartErrorMessage(error: unknown) {
  if (error instanceof DOMException) {
    switch (error.name) {
      case 'NotAllowedError':
      case 'SecurityError':
        return buildPermissionDeniedMessage()
      case 'NotFoundError':
        return '未检测到可用的麦克风设备，请检查手机录音输入。'
      case 'NotReadableError':
      case 'TrackStartError':
        return '麦克风当前不可用，请关闭其他正在占用录音的应用后重试。'
      default:
        return getChineseErrorMessage(error.message, '录音启动失败，请稍后重试。')
    }
  }

  return error instanceof Error ? getChineseErrorMessage(error.message, '录音启动失败，请稍后重试。') : '录音启动失败，请稍后重试。'
}

function getChineseErrorMessage(message: string | undefined, fallback: string) {
  return message && /[\u4e00-\u9fff]/.test(message) ? message : fallback
}

function hasSecureVoiceContext() {
  return typeof window !== 'undefined' && window.isSecureContext
}

function isRecorderSupported() {
  return (
    typeof window !== 'undefined' &&
    typeof MediaRecorder !== 'undefined' &&
    typeof navigator !== 'undefined' &&
    typeof navigator.mediaDevices?.getUserMedia === 'function'
  )
}

function pickSupportedMimeType() {
  if (typeof MediaRecorder === 'undefined' || typeof MediaRecorder.isTypeSupported !== 'function') {
    return ''
  }

  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus',
  ]

  return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate)) || ''
}

function getFilenameForMimeType(mimeType: string) {
  if (mimeType.includes('mp4')) {
    return 'daily-intake-recording.mp4'
  }
  if (mimeType.includes('ogg')) {
    return 'daily-intake-recording.ogg'
  }
  return 'daily-intake-recording.webm'
}

const BAR_COUNT = 20

export function useSpeechInput() {
  const errorMessage = ref('')
  const state = ref<DailyIntakeSpeechState>('idle')
  const recordedAudio = ref<RecordedAudioPayload | null>(null)
  const audioLevelBars: Ref<number[]> = ref(Array(BAR_COUNT).fill(0))

  let mediaRecorder: MediaRecorder | null = null
  let mediaStream: MediaStream | null = null
  let recordedChunks: BlobPart[] = []
  let stopRequested = false
  let audioContext: AudioContext | null = null
  let analyserNode: AnalyserNode | null = null
  let animFrameId: number | null = null

  const supported = isRecorderSupported()
  const compatibilityHint =
    '当前使用浏览器录音并交给服务端转写，稳定性优先于浏览器内置语音识别。'

  if (!supported) {
    state.value = 'unsupported'
  }

  const resetError = () => {
    errorMessage.value = ''
  }

  const stopAnalyser = () => {
    if (animFrameId !== null) {
      cancelAnimationFrame(animFrameId)
      animFrameId = null
    }
    analyserNode = null
    try {
      audioContext?.close()
    } catch {
      // ignore
    }
    audioContext = null
    audioLevelBars.value = Array(BAR_COUNT).fill(0)
  }

  const startAnalyser = (stream: MediaStream) => {
    try {
      audioContext = new AudioContext()
      analyserNode = audioContext.createAnalyser()
      analyserNode.fftSize = 128
      const source = audioContext.createMediaStreamSource(stream)
      source.connect(analyserNode)

      const binCount = analyserNode.frequencyBinCount // 64
      const dataArray = new Uint8Array(binCount)
      const binsPerBar = Math.floor(binCount / BAR_COUNT)

      const tick = () => {
        if (!analyserNode) return
        analyserNode.getByteFrequencyData(dataArray)
        const bars: number[] = []
        for (let i = 0; i < BAR_COUNT; i++) {
          let sum = 0
          for (let j = 0; j < binsPerBar; j++) {
            sum += dataArray[i * binsPerBar + j]
          }
          bars.push(Math.min(sum / binsPerBar / 255, 1))
        }
        audioLevelBars.value = bars
        animFrameId = requestAnimationFrame(tick)
      }
      tick()
    } catch {
      // AudioContext not available (e.g. tests)
    }
  }

  const cleanupStream = () => {
    stopAnalyser()
    if (!mediaStream) {
      return
    }
    for (const track of mediaStream.getTracks()) {
      track.stop()
    }
    mediaStream = null
  }

  const detachRecorder = () => {
    if (!mediaRecorder) {
      return
    }
    mediaRecorder.onstart = null
    mediaRecorder.ondataavailable = null
    mediaRecorder.onerror = null
    mediaRecorder.onstop = null
    mediaRecorder = null
  }

  const finalizeRecording = () => {
    if (!recordedChunks.length) {
      return
    }

    const mimeType = mediaRecorder?.mimeType || pickSupportedMimeType() || 'audio/webm'
    const blob = new Blob(recordedChunks, { type: mimeType })
    recordedAudio.value = {
      blob,
      filename: getFilenameForMimeType(mimeType),
      mimeType,
    }
    recordedChunks = []
  }

  const teardownRecorder = () => {
    detachRecorder()
    cleanupStream()
  }

  const startListening = async () => {
    if (!supported) {
      state.value = 'unsupported'
      errorMessage.value = buildRecorderUnavailableMessage()
      return false
    }

    if (!hasSecureVoiceContext()) {
      state.value = 'blocked'
      errorMessage.value = buildInsecureContextMessage()
      return false
    }

    resetError()
    recordedAudio.value = null
    recordedChunks = []
    stopRequested = false
    state.value = 'authorizing'

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
    } catch (error) {
      state.value =
        error instanceof DOMException &&
        (error.name === 'NotAllowedError' || error.name === 'SecurityError')
          ? 'permission-denied'
          : 'error'
      errorMessage.value = buildRecorderStartErrorMessage(error)
      cleanupStream()
      return false
    }

    try {
      const mimeType = pickSupportedMimeType()
      mediaRecorder = mimeType ? new MediaRecorder(mediaStream, { mimeType }) : new MediaRecorder(mediaStream)
    } catch (error) {
      state.value = 'error'
      errorMessage.value = buildRecorderStartErrorMessage(error)
      cleanupStream()
      detachRecorder()
      return false
    }

    mediaRecorder.onstart = () => {
      state.value = 'listening'
      startAnalyser(mediaStream!)
    }

    mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        recordedChunks.push(event.data)
      }
    }

    mediaRecorder.onerror = (event: Event) => {
      const recorderError = 'error' in event ? (event as MediaRecorderErrorEventLike).error : null
      state.value = 'error'
      errorMessage.value =
        getChineseErrorMessage(recorderError?.message, '录音过程中出现异常，请重新开始。')
      teardownRecorder()
    }

    mediaRecorder.onstop = () => {
      finalizeRecording()
      teardownRecorder()

      if (state.value === 'parsing' || state.value === 'error') {
        return
      }

      if (stopRequested) {
        state.value = 'idle'
        return
      }

      state.value = 'idle'
    }

    mediaRecorder.start()
    return true
  }

  const stopListening = () => {
    stopRequested = true
    if (!mediaRecorder) {
      state.value = 'idle'
      cleanupStream()
      return
    }

    if (mediaRecorder.state === 'inactive') {
      state.value = 'idle'
      teardownRecorder()
      return
    }

    mediaRecorder.stop()
  }

  const abortListening = () => {
    stopRequested = true
    recordedAudio.value = null
    recordedChunks = []

    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
      return
    }

    teardownRecorder()
    if (supported) {
      state.value = 'idle'
    }
  }

  const setParsing = () => {
    state.value = 'parsing'
  }

  const markIdle = () => {
    if (supported) {
      state.value = 'idle'
    }
  }

  const consumeRecordedAudio = () => {
    const value = recordedAudio.value
    recordedAudio.value = null
    return value
  }

  onBeforeUnmount(() => {
    stopRequested = true
    teardownRecorder()
  })

  return {
    audioLevelBars,
    errorMessage,
    state,
    supported,
    compatibilityHint,
    startListening,
    stopListening,
    abortListening,
    setParsing,
    markIdle,
    consumeRecordedAudio,
  }
}
