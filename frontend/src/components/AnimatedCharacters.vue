<template>
  <div class="left-panel">
    <div class="logo">
      <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
        <path d="M12 2L15 9H9L12 2Z" />
        <path d="M12 22L9 15H15L12 22Z" />
        <path d="M2 12L9 9V15L2 12Z" />
        <path d="M22 12L15 15V9L22 12Z" />
      </svg>
      <span>滨鲜工作台</span>
    </div>
    <div class="characters-wrapper">
      <div class="characters-scene" ref="sceneRef">
        <div class="character char-purple" :style="s.purple">
          <div class="eyes" :class="{ 'shake-head': shakeHeads }" :style="s.purpleEyes">
            <div class="eyeball" :style="s.purpleEyeL">
              <div class="pupil" :style="s.purplePupilL"></div>
            </div>
            <div class="eyeball" :style="s.purpleEyeR">
              <div class="pupil" :style="s.purplePupilR"></div>
            </div>
          </div>
        </div>
        <div class="character char-black" :style="s.black">
          <div class="eyes" :class="{ 'shake-head': shakeHeads }" :style="s.blackEyes">
            <div class="eyeball" :style="s.blackEyeL">
              <div class="pupil" :style="s.blackPupilL"></div>
            </div>
            <div class="eyeball" :style="s.blackEyeR">
              <div class="pupil" :style="s.blackPupilR"></div>
            </div>
          </div>
        </div>
        <div class="character char-orange" :style="s.orange">
          <div class="eyes" :class="{ 'shake-head': shakeHeads }" :style="s.orangeEyes">
            <div class="bare-pupil" :style="s.orangePupilL"></div>
            <div class="bare-pupil" :style="s.orangePupilR"></div>
          </div>
          <div class="orange-mouth" :class="{ visible: s.orangeMouthVisible, 'shake-head': shakeHeads }" :style="s.orangeMouth"></div>
        </div>
        <div class="character char-yellow" :style="s.yellow">
          <div class="eyes" :class="{ 'shake-head': shakeHeads }" :style="s.yellowEyes">
            <div class="bare-pupil" :style="s.yellowPupilL"></div>
            <div class="bare-pupil" :style="s.yellowPupilR"></div>
          </div>
          <div class="yellow-mouth" :class="{ 'shake-head': shakeHeads }" :style="s.yellowMouth"></div>
        </div>
        <div v-for="p in successParticles" :key="p.id" class="success-particle"
          :style="{
            left: p.x + 'px', top: p.y + 'px',
            width: p.size + 'px', height: p.size + 'px',
            background: p.color,
            '--dx': p.dx + 'px', '--dy': p.dy + 'px',
            animationDelay: p.delay + 's',
          }">
        </div>
      </div>
    </div>
    <div class="bubble-layer" :class="{ paused: bubblesPaused }">
      <div v-for="b in bubbles" :key="b.id" class="bubble"
        :style="{
          width: b.size + 'px', height: b.size + 'px',
          left: b.left + '%',
          bottom: b.bottom + '%',
          background: b.color,
          filter: 'blur(' + b.blur + 'px)',
          '--bubble-duration': b.duration + 's',
          '--bubble-delay': b.delay + 's',
        }">
      </div>
    </div>
    <div class="footer-links">
      <a href="#">隐私政策</a>
      <a href="#">服务条款</a>
      <a href="#">联系我们</a>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, onMounted, onUnmounted, ref, watch } from 'vue'

interface Particle {
  id: number
  x: number
  y: number
  dx: number
  dy: number
  color: string
  delay: number
  size: number
}

const successParticles = ref<Particle[]>([])

const props = defineProps<{
  typing: boolean
  passwordFocused: boolean
  showPassword: boolean
  loginError: boolean
  isRegister?: boolean
}>()

const emit = defineEmits<{
  errorAnimated: []
}>()

const sceneRef = ref<HTMLElement | null>(null)

let mouseX = 0
let mouseY = 0
let isLookingAtEachOther = false
let isPurpleBlinking = false
let isBlackBlinking = false
let isPurplePeeking = false
let isLoginError = false
let isRegisterMode = false
let interactionTimer: ReturnType<typeof setTimeout> | null = null
let characterInteraction = ''
let typingTimer: ReturnType<typeof setTimeout> | null = null
let purpleBlinkTimer: ReturnType<typeof setTimeout> | null = null
let blackBlinkTimer: ReturnType<typeof setTimeout> | null = null
let peekTimer: ReturnType<typeof setTimeout> | null = null

const shakeHeads = ref(false)
const bubblesPaused = ref(false)
const bubbles = ref<Bubble[]>([])

const FLOAT_CONFIG = {
  purple: { amp: 4, period: 4000, phase: 0 },
  black: { amp: 3, period: 3500, phase: 0.75 },
  orange: { amp: 5, period: 5000, phase: 0.3 },
  yellow: { amp: 2, period: 4500, phase: 1.2 },
} as const
let floatStartTime = 0
let floatTimer: ReturnType<typeof setInterval> | null = null

function calcPosition(el: HTMLElement) {
  const rect = el.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 3
  const dx = mouseX - cx
  const dy = mouseY - cy
  return {
    faceX: Math.max(-15, Math.min(15, dx / 20)),
    faceY: Math.max(-10, Math.min(10, dy / 30)),
    bodySkew: Math.max(-6, Math.min(6, -dx / 120)),
  }
}

function calcPupilOffset(el: HTMLElement, maxDist: number) {
  const rect = el.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 2
  const dx = mouseX - cx
  const dy = mouseY - cy
  const dist = Math.min(Math.sqrt(dx * dx + dy * dy), maxDist)
  const angle = Math.atan2(dy, dx)
  return { x: Math.cos(angle) * dist, y: Math.sin(angle) * dist }
}

interface Bubble {
  id: number
  size: number
  left: number
  bottom: number
  color: string
  blur: number
  duration: number
  delay: number
}

interface Styles {
  purple: Record<string, string>
  purpleEyes: Record<string, string>
  purpleEyeL: Record<string, string>
  purpleEyeR: Record<string, string>
  purplePupilL: Record<string, string>
  purplePupilR: Record<string, string>
  black: Record<string, string>
  blackEyes: Record<string, string>
  blackEyeL: Record<string, string>
  blackEyeR: Record<string, string>
  blackPupilL: Record<string, string>
  blackPupilR: Record<string, string>
  orange: Record<string, string>
  orangeEyes: Record<string, string>
  orangePupilL: Record<string, string>
  orangePupilR: Record<string, string>
  orangeMouth: Record<string, string>
  orangeMouthVisible: boolean
  yellow: Record<string, string>
  yellowEyes: Record<string, string>
  yellowPupilL: Record<string, string>
  yellowPupilR: Record<string, string>
  yellowMouth: Record<string, string>
}

const s = reactive<Styles>({
  purple: { height: '370px' },
  purpleEyes: { left: '45px', top: '40px' },
  purpleEyeL: { height: '18px', width: '18px', borderRadius: '50%', background: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
  purpleEyeR: { height: '18px', width: '18px', borderRadius: '50%', background: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
  purplePupilL: { width: '7px', height: '7px' },
  purplePupilR: { width: '7px', height: '7px' },
  black: {},
  blackEyes: { left: '26px', top: '32px' },
  blackEyeL: { height: '16px', width: '16px' },
  blackEyeR: { height: '16px', width: '16px' },
  blackPupilL: { width: '6px', height: '6px' },
  blackPupilR: { width: '6px', height: '6px' },
  orange: {},
  orangeEyes: { left: '82px', top: '90px' },
  orangePupilL: {},
  orangePupilR: {},
  orangeMouth: {},
  orangeMouthVisible: false,
  yellow: {},
  yellowEyes: { left: '52px', top: '40px' },
  yellowPupilL: {},
  yellowPupilR: {},
  yellowMouth: { left: '40px', top: '88px' },
})

function update() {
  if (!sceneRef.value) return
  const chars = sceneRef.value.querySelectorAll<HTMLElement>('.character')
  if (chars.length < 4) return
  const purple = chars[0]
  const black = chars[1]
  const orange = chars[2]
  const yellow = chars[3]

  const purplePos = calcPosition(purple)
  const blackPos = calcPosition(black)
  const orangePos = calcPosition(orange)
  const yellowPos = calcPosition(yellow)

  const showPwd = props.showPassword
  const isLookingAway = props.passwordFocused && !showPwd

  s.purple = {
    transform: isLoginError ? 'skewX(0deg)' : isLookingAway ? 'skewX(-14deg) translateX(-20px)' : props.typing ? `skewX(${(purplePos.bodySkew || 0) - 12}deg) translateX(40px)` : `skewX(${purplePos.bodySkew}deg)`,
    height: isLookingAway || props.typing ? '410px' : '370px',
  }

  const pEyeL = purple.querySelector<HTMLElement>('.eyeball')
  const pEyeR = purple.querySelector<HTMLElement>('.eyeball:last-child')
  if (pEyeL && pEyeR) {
    s.purpleEyeL = { height: isPurpleBlinking ? '2px' : '18px', width: '18px', borderRadius: '50%', background: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }
    s.purpleEyeR = { height: isPurpleBlinking ? '2px' : '18px', width: '18px', borderRadius: '50%', background: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }
  }

  const pupilSize = '7px'
  if (isLoginError) {
    s.purpleEyes = { left: '30px', top: '55px' }
    s.purplePupilL = { transform: 'translate(-3px, 4px)', width: pupilSize, height: pupilSize }
    s.purplePupilR = { transform: 'translate(-3px, 4px)', width: pupilSize, height: pupilSize }
  } else if (isLookingAway) {
    s.purpleEyes = { left: '20px', top: '25px' }
    s.purplePupilL = { transform: 'translate(-5px, -5px)', width: pupilSize, height: pupilSize }
    s.purplePupilR = { transform: 'translate(-5px, -5px)', width: pupilSize, height: pupilSize }
  } else if (showPwd) {
    s.purpleEyes = { left: '20px', top: '35px' }
    const px = isPurplePeeking ? 4 : -4
    const py = isPurplePeeking ? 5 : -4
    s.purplePupilL = { transform: `translate(${px}px, ${py}px)`, width: pupilSize, height: pupilSize }
    s.purplePupilR = { transform: `translate(${px}px, ${py}px)`, width: pupilSize, height: pupilSize }
  } else if (isLookingAtEachOther) {
    s.purpleEyes = { left: '55px', top: '65px' }
    s.purplePupilL = { transform: 'translate(3px, 4px)', width: pupilSize, height: pupilSize }
    s.purplePupilR = { transform: 'translate(3px, 4px)', width: pupilSize, height: pupilSize }
  } else if (isRegisterMode) {
    s.purple = { transform: 'skewX(-10deg) translateX(-15px)', height: '370px' }
    s.purpleEyes = { left: '20px', top: '35px' }
    s.purplePupilL = { transform: 'translate(-5px, -3px)', width: pupilSize, height: pupilSize }
    s.purplePupilR = { transform: 'translate(-5px, -3px)', width: pupilSize, height: pupilSize }
  } else {
    s.purpleEyes = { left: `${45 + purplePos.faceX}px`, top: `${40 + purplePos.faceY}px` }
    if (pEyeL) {
      const po = characterInteraction === 'purpleGlance' ? { x: 5, y: 0 } : calcPupilOffset(pEyeL, 5)
      s.purplePupilL = { transform: `translate(${po.x}px, ${po.y}px)`, width: pupilSize, height: pupilSize }
      s.purplePupilR = { transform: `translate(${po.x}px, ${po.y}px)`, width: pupilSize, height: pupilSize }
    }
  }

  const bEyeL = black.querySelector<HTMLElement>('.eyeball')
  const bEyeR = black.querySelector<HTMLElement>('.eyeball:last-child')
  if (bEyeL && bEyeR) {
    s.blackEyeL = { height: isBlackBlinking ? '2px' : '16px', width: '16px', borderRadius: '50%', background: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }
    s.blackEyeR = { height: isBlackBlinking ? '2px' : '16px', width: '16px', borderRadius: '50%', background: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }
  }

  const bPupilSize = '6px'
  if (isLoginError) {
    s.blackEyes = { left: '15px', top: '40px' }
    s.blackPupilL = { transform: 'translate(-3px, 4px)', width: bPupilSize, height: bPupilSize }
    s.blackPupilR = { transform: 'translate(-3px, 4px)', width: bPupilSize, height: bPupilSize }
  } else if (isLookingAway) {
    s.blackEyes = { left: '10px', top: '20px' }
    s.blackPupilL = { transform: 'translate(-4px, -5px)', width: bPupilSize, height: bPupilSize }
    s.blackPupilR = { transform: 'translate(-4px, -5px)', width: bPupilSize, height: bPupilSize }
  } else if (showPwd) {
    s.blackEyes = { left: '10px', top: '28px' }
    s.blackPupilL = { transform: 'translate(-4px, -4px)', width: bPupilSize, height: bPupilSize }
    s.blackPupilR = { transform: 'translate(-4px, -4px)', width: bPupilSize, height: bPupilSize }
  } else if (isLookingAtEachOther) {
    s.blackEyes = { left: '32px', top: '12px' }
    s.blackPupilL = { transform: 'translate(0px, -4px)', width: bPupilSize, height: bPupilSize }
    s.blackPupilR = { transform: 'translate(0px, -4px)', width: bPupilSize, height: bPupilSize }
  } else if (isRegisterMode) {
    s.blackEyes = { left: '28px', top: '22px' }
    s.blackPupilL = { transform: 'translate(0px, -2px)', width: bPupilSize, height: bPupilSize }
    s.blackPupilR = { transform: 'translate(0px, -2px)', width: bPupilSize, height: bPupilSize }
  } else {
    s.blackEyes = { left: `${26 + blackPos.faceX}px`, top: `${32 + blackPos.faceY}px` }
    if (bEyeL) {
      const bo = characterInteraction === 'blackWave' ? { x: -3, y: -3 } : calcPupilOffset(bEyeL, 4)
      s.blackPupilL = { transform: `translate(${bo.x}px, ${bo.y}px)`, width: bPupilSize, height: bPupilSize }
      s.blackPupilR = { transform: `translate(${bo.x}px, ${bo.y}px)`, width: bPupilSize, height: bPupilSize }
    }
  }

  s.black = {
    transform: isRegisterMode ? 'skewX(8deg) translateX(15px)' : isLoginError ? 'skewX(0deg)' : isLookingAway ? 'skewX(12deg) translateX(-10px)' : isLookingAtEachOther ? `skewX(${(blackPos.bodySkew || 0) * 1.5 + 10}deg) translateX(20px)` : props.typing ? `skewX(${(blackPos.bodySkew || 0) * 1.5}deg)` : `skewX(${blackPos.bodySkew}deg)`,
  }

  s.orange = { transform: isRegisterMode ? 'skewX(4deg)' : showPwd ? 'skewX(0deg)' : `skewX(${orangePos.bodySkew}deg)` }

  const oPupils = orange.querySelectorAll<HTMLElement>('.bare-pupil')
  if (isLoginError) {
    s.orangeEyes = { left: '60px', top: '95px' }
    if (oPupils.length >= 2) {
      s.orangePupilL = { transform: 'translate(-3px, 4px)' }
      s.orangePupilR = { transform: 'translate(-3px, 4px)' }
    }
    s.orangeMouth = { left: `${80 + orangePos.faceX}px`, top: '130px' }
    s.orangeMouthVisible = true
  } else if (isLookingAway) {
    s.orangeEyes = { left: '50px', top: '75px' }
    if (oPupils.length >= 2) {
      s.orangePupilL = { transform: 'translate(-5px, -5px)' }
      s.orangePupilR = { transform: 'translate(-5px, -5px)' }
    }
    s.orangeMouthVisible = false
  } else if (showPwd) {
    s.orangeEyes = { left: '50px', top: '85px' }
    if (oPupils.length >= 2) {
      s.orangePupilL = { transform: 'translate(-5px, -4px)' }
      s.orangePupilR = { transform: 'translate(-5px, -4px)' }
    }
    s.orangeMouthVisible = false
  } else if (isRegisterMode) {
    s.orangeEyes = { left: '78px', top: '85px' }
    if (oPupils.length >= 2) {
      s.orangePupilL = { transform: 'translate(2px, 0px)' }
      s.orangePupilR = { transform: 'translate(2px, 0px)' }
    }
    s.orangeMouth = { left: `${80 + orangePos.faceX}px`, top: '130px' }
    s.orangeMouthVisible = false
  } else {
    s.orangeEyes = { left: `${82 + orangePos.faceX}px`, top: `${90 + orangePos.faceY}px` }
    if (oPupils.length >= 2) {
      const oo = characterInteraction === 'orangeTilt' ? { x: 3, y: 2 } : calcPupilOffset(oPupils[0], 5)
      s.orangePupilL = { transform: `translate(${oo.x}px, ${oo.y}px)` }
      s.orangePupilR = { transform: `translate(${oo.x}px, ${oo.y}px)` }
    }
    s.orangeMouth = { left: `${80 + orangePos.faceX}px`, top: '130px' }
    s.orangeMouthVisible = false
  }

  s.yellow = { transform: isRegisterMode ? 'skewX(-2deg)' : showPwd ? 'skewX(0deg)' : `skewX(${yellowPos.bodySkew}deg)` }

  const yPupils = yellow.querySelectorAll<HTMLElement>('.bare-pupil')
  if (isLoginError) {
    s.yellowEyes = { left: '35px', top: '45px' }
    if (yPupils.length >= 2) {
      s.yellowPupilL = { transform: 'translate(-3px, 4px)' }
      s.yellowPupilR = { transform: 'translate(-3px, 4px)' }
    }
    s.yellowMouth = { left: '30px', top: '92px', transform: 'rotate(-8deg)' }
  } else if (isLookingAway) {
    s.yellowEyes = { left: '20px', top: '30px' }
    if (yPupils.length >= 2) {
      s.yellowPupilL = { transform: 'translate(-5px, -5px)' }
      s.yellowPupilR = { transform: 'translate(-5px, -5px)' }
    }
    s.yellowMouth = { left: '15px', top: '78px', transform: 'rotate(0deg)' }
  } else if (showPwd) {
    s.yellowEyes = { left: '20px', top: '35px' }
    if (yPupils.length >= 2) {
      s.yellowPupilL = { transform: 'translate(-5px, -4px)' }
      s.yellowPupilR = { transform: 'translate(-5px, -4px)' }
    }
    s.yellowMouth = { left: '10px', top: '88px', transform: 'rotate(0deg)' }
  } else if (isRegisterMode) {
    s.yellowEyes = { left: '50px', top: '38px' }
    if (yPupils.length >= 2) {
      s.yellowPupilL = { transform: 'translate(0px, -1px)' }
      s.yellowPupilR = { transform: 'translate(0px, -1px)' }
    }
    s.yellowMouth = { left: '38px', top: '86px', transform: 'rotate(4deg)' }
  } else {
    s.yellowEyes = { left: `${52 + yellowPos.faceX}px`, top: `${40 + yellowPos.faceY}px` }
    if (yPupils.length >= 2) {
      const yo = characterInteraction === 'yellowNod' ? { x: 0, y: -2 } : calcPupilOffset(yPupils[0], 5)
      s.yellowPupilL = { transform: `translate(${yo.x}px, ${yo.y}px)` }
      s.yellowPupilR = { transform: `translate(${yo.x}px, ${yo.y}px)` }
    }
    s.yellowMouth = { left: `${40 + yellowPos.faceX}px`, top: `${88 + yellowPos.faceY}px`, transform: 'rotate(0deg)' }
  }
  if (floatStartTime > 0) {
    const elapsed = performance.now() - floatStartTime
    const floatY = (cfg: { amp: number; period: number; phase: number }) =>
      -cfg.amp * 0.5 * (1 - Math.cos((elapsed / cfg.period + cfg.phase) * Math.PI * 2))
    s.purple.transform += ` translateY(${floatY(FLOAT_CONFIG.purple)}px)`
    s.black.transform += ` translateY(${floatY(FLOAT_CONFIG.black)}px)`
    s.orange.transform += ` translateY(${floatY(FLOAT_CONFIG.orange)}px)`
    s.yellow.transform += ` translateY(${floatY(FLOAT_CONFIG.yellow)}px)`
  }
}

function initBubbles() {
  const colors = ['rgba(133,85,255,0.7)', 'rgba(255,112,67,0.6)', 'rgba(255,213,79,0.5)']
  const items: Bubble[] = []
  for (let i = 0; i < 8; i++) {
    items.push({
      id: i,
      size: Math.random() * 50 + 30,
      left: Math.random() * 80 + 5,
      bottom: Math.random() * 40,
      color: colors[i % 3],
      blur: Math.random() * 4 + 2,
      duration: Math.random() * 4 + 5,
      delay: Math.random() * 4,
    })
  }
  bubbles.value = items
}

function scheduleInteraction() {
  interactionTimer = setTimeout(() => {
    const actions = ['purpleGlance', 'blackWave', 'orangeTilt', 'yellowNod']
    characterInteraction = actions[Math.floor(Math.random() * actions.length)]
    update()
    interactionTimer = setTimeout(() => {
      characterInteraction = ''
      update()
      scheduleInteraction()
    }, 2000)
  }, Math.random() * 4000 + 8000)
}

let errorRecoverTimer: ReturnType<typeof setTimeout> | null = null
let errorShakeTimer: ReturnType<typeof setTimeout> | null = null

function triggerError() {
  if (errorRecoverTimer) {
    clearTimeout(errorRecoverTimer)
    errorRecoverTimer = null
  }
  if (errorShakeTimer) {
    clearTimeout(errorShakeTimer)
    errorShakeTimer = null
  }
  shakeHeads.value = false
  void document.body.offsetHeight
  isLoginError = true
  bubblesPaused.value = true
  update()
  errorShakeTimer = setTimeout(() => {
    shakeHeads.value = true
  }, 350)
  errorRecoverTimer = setTimeout(() => {
    isLoginError = false
    bubblesPaused.value = false
    shakeHeads.value = false
    errorRecoverTimer = null
    update()
    emit('errorAnimated')
  }, 2500)
}

function triggerSuccess() {
  const colors = ['#8555ff', '#3d3d5c', '#ff7043', '#ffd54f']
  const scene = sceneRef.value
  if (!scene) return
  const rect = scene.getBoundingClientRect()
  const cx = rect.width / 2
  const cy = rect.height / 2
  const items: Particle[] = []
  let pid = 0
  for (const charClass of ['.char-purple', '.char-black', '.char-orange', '.char-yellow']) {
    const el = scene.querySelector<HTMLElement>(charClass)
    if (!el) continue
    const cr = el.getBoundingClientRect()
    const originX = cr.left - rect.left + cr.width / 2
    const originY = cr.top - rect.top + cr.height / 2
    for (let i = 0; i < 8; i++) {
      const angle = Math.random() * Math.PI * 2
      const dist = Math.random() * 60 + 30
      items.push({
        id: pid++, x: originX, y: originY,
        dx: Math.cos(angle) * dist, dy: Math.sin(angle) * dist,
        color: colors[charClass === '.char-yellow' ? 3 : charClass === '.char-orange' ? 2 : charClass === '.char-black' ? 1 : 0],
        delay: Math.random() * 0.3,
        size: Math.random() * 6 + 4,
      })
    }
  }
  successParticles.value = items
  setTimeout(() => { successParticles.value = [] }, 1800)
}

function startFloat() {
  floatStartTime = performance.now()
  if (floatTimer !== null) clearInterval(floatTimer)
  floatTimer = setInterval(update, 30)
}

function stopFloat() {
  if (floatTimer !== null) {
    clearInterval(floatTimer)
    floatTimer = null
  }
}

function setTyping(typing: boolean) {
  if (typing) {
    isLookingAtEachOther = true
    if (typingTimer) clearTimeout(typingTimer)
    typingTimer = setTimeout(() => {
      isLookingAtEachOther = false
      update()
    }, 800)
  } else {
    isLookingAtEachOther = false
  }
  update()
}

function scheduleBlinkPurple() {
  purpleBlinkTimer = setTimeout(() => {
    isPurpleBlinking = true
    update()
    purpleBlinkTimer = setTimeout(() => {
      isPurpleBlinking = false
      update()
      scheduleBlinkPurple()
    }, 150)
  }, Math.random() * 4000 + 3000)
}

function scheduleBlinkBlack() {
  blackBlinkTimer = setTimeout(() => {
    isBlackBlinking = true
    update()
    blackBlinkTimer = setTimeout(() => {
      isBlackBlinking = false
      update()
      scheduleBlinkBlack()
    }, 150)
  }, Math.random() * 4000 + 3000)
}

function schedulePeek() {
  peekTimer = setTimeout(() => {
    isPurplePeeking = true
    update()
    peekTimer = setTimeout(() => {
      isPurplePeeking = false
      update()
      schedulePeek()
    }, 800)
  }, Math.random() * 3000 + 2000)
}

function onMouseMove(e: MouseEvent) {
  mouseX = e.clientX
  mouseY = e.clientY
  if (!props.typing && !isLoginError) update()
}

watch(() => props.typing, (val) => {
  setTyping(val)
})
watch(() => props.passwordFocused, () => { update() })
watch(() => props.showPassword, () => { if (props.showPassword) schedulePeek(); update() })
watch(() => props.loginError, (val) => { if (val) triggerError() })
watch(() => props.isRegister, (val) => { isRegisterMode = !!val; update() }, { immediate: true })

let reducedMotion = false

function handleVisibilityChange() {
  if (document.hidden && floatTimer !== null) stopFloat()
  else if (!document.hidden && floatTimer === null && !reducedMotion) startFloat()
}

onMounted(() => {
  window.addEventListener('mousemove', onMouseMove)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (!reducedMotion) startFloat()
  scheduleBlinkPurple()
  scheduleBlinkBlack()
  initBubbles()
  scheduleInteraction()
  update()
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  stopFloat()
  if (typingTimer) clearTimeout(typingTimer)
  if (purpleBlinkTimer) clearTimeout(purpleBlinkTimer)
  if (blackBlinkTimer) clearTimeout(blackBlinkTimer)
  if (peekTimer) clearTimeout(peekTimer)
  if (errorRecoverTimer) clearTimeout(errorRecoverTimer)
  if (errorShakeTimer) clearTimeout(errorShakeTimer)
  if (interactionTimer) clearTimeout(interactionTimer)
})

defineExpose({ triggerError, triggerSuccess })
</script>

<style scoped>
.left-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: linear-gradient(135deg, #d4d0dc 0%, #c8c4d0 30%, #bbb7c5 50%, #c8c4d0 70%, #d4d0dc 100%);
  background-size: 300% 300%;
  animation: panelShift 20s ease infinite;
  padding: 40px 48px;
  overflow: hidden;
  min-height: 100vh;
}

.left-panel .logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  z-index: 10;
  position: relative;
}

.left-panel .logo svg {
  width: 28px;
  height: 28px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(8px);
  padding: 4px;
  border-radius: 6px;
}

.characters-wrapper {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  height: 420px;
}

.left-panel .footer-links {
  display: flex;
  gap: 28px;
  font-size: 13px;
  color: rgba(80, 70, 90, 0.7);
  z-index: 10;
  position: relative;
}

.left-panel .footer-links a {
  color: inherit;
  text-decoration: none;
  transition: color 0.2s;
}

.left-panel .footer-links a:hover {
  color: #333;
}

.left-panel::after {
  content: "";
  position: absolute;
  top: 20%;
  right: 15%;
  width: 260px;
  height: 260px;
  background: rgba(180, 170, 200, 0.25);
  border-radius: 50%;
  filter: blur(80px);
}

.left-panel::before {
  content: "";
  position: absolute;
  bottom: 15%;
  left: 10%;
  width: 350px;
  height: 350px;
  background: rgba(200, 195, 210, 0.2);
  border-radius: 50%;
  filter: blur(100px);
}

.characters-scene {
  position: relative;
  width: 480px;
  height: 360px;
}

.character {
  position: absolute;
  bottom: 0;
  transition: all 0.7s ease-in-out;
  transform-origin: bottom center;
  will-change: transform;
}

.char-purple {
  left: 60px;
  width: 170px;
  height: 370px;
  background: linear-gradient(180deg, #8555ff 0%, #a78bfa 100%);
  border-radius: 10px 10px 0 0;
  z-index: 1;
}

.char-black {
  left: 220px;
  width: 115px;
  height: 290px;
  background: linear-gradient(180deg, #1a1a2e 0%, #3d3d5c 100%);
  border-radius: 8px 8px 0 0;
  z-index: 2;
}

.char-orange {
  left: 0;
  width: 230px;
  height: 190px;
  background: linear-gradient(180deg, #ff7043 0%, #ff9b6b 100%);
  border-radius: 115px 115px 0 0;
  z-index: 3;
}

.char-yellow {
  left: 290px;
  width: 135px;
  height: 215px;
  background: linear-gradient(180deg, #ffd54f 0%, #ffe082 100%);
  border-radius: 68px 68px 0 0;
  z-index: 4;
}

.eyes {
  position: absolute;
  display: flex;
  transition: left 0.7s ease-in-out, top 0.7s ease-in-out;
}

.char-purple .eyes { gap: 28px; }
.char-black .eyes { gap: 20px; }
.char-orange .eyes { gap: 28px; }
.char-yellow .eyes { gap: 20px; }

.eyeball {
  transition: height 0.15s ease;
}

.pupil {
  border-radius: 50%;
  background: #2d2d2d;
  transition: transform 0.1s ease-out;
}

.bare-pupil {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #2d2d2d;
  transition: transform 0.7s ease-in-out;
}

.yellow-mouth {
  position: absolute;
  width: 50px;
  height: 4px;
  background: #2d2d2d;
  border-radius: 2px;
  transition: left 0.7s ease-in-out, top 0.7s ease-in-out, transform 0.7s ease-in-out;
}

.orange-mouth {
  position: absolute;
  width: 28px;
  height: 14px;
  border: 3px solid #2d2d2d;
  border-top: none;
  border-radius: 0 0 14px 14px;
  opacity: 0;
  transition: left 0.7s ease-in-out, top 0.7s ease-in-out, opacity 0.7s ease-in-out;
}

.orange-mouth.visible {
  opacity: 1;
}

@keyframes panelShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

@keyframes shakeHead {
  0%, 100% { translate: 0 0; }
  10% { translate: -9px 0; }
  20% { translate: 7px 0; }
  30% { translate: -6px 0; }
  40% { translate: 5px 0; }
  50% { translate: -4px 0; }
  60% { translate: 3px 0; }
  70% { translate: -2px 0; }
  80% { translate: 1px 0; }
  90% { translate: -0.5px 0; }
}

.eyes.shake-head,
.yellow-mouth.shake-head,
.orange-mouth.shake-head {
  animation: shakeHead 0.8s cubic-bezier(0.36, 0.07, 0.19, 0.97) both;
}

@keyframes bubbleUp {
  0% { transform: translateY(0) translateX(0) scale(0.3); opacity: 0; }
  5% { opacity: 0.5; }
  15% { opacity: 0.5; }
  85% { opacity: 0.2; }
  100% { transform: translateY(-60vh) translateX(20px) scale(1.1); opacity: 0; }
}
.bubble-layer {
  position: absolute;
  inset: 0;
  overflow: hidden;
  z-index: 1;
  pointer-events: none;
}
.bubble-layer.paused .bubble {
  animation-play-state: paused;
}
.bubble {
  position: absolute;
  border-radius: 50%;
  will-change: transform;
  animation: bubbleUp var(--bubble-duration, 7s) linear var(--bubble-delay, 0s) infinite;
}

.success-particle {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  z-index: 10;
  animation: particleBurst 0.8s ease-out forwards;
  opacity: 0;
}
@keyframes particleBurst {
  0% { opacity: 1; transform: translate(0, 0) scale(0.5); }
  40% { opacity: 1; transform: translate(calc(var(--dx) * 0.6), calc(var(--dy) * 0.6)) scale(1); }
  100% { opacity: 0; transform: translate(var(--dx), var(--dy)) scale(0.3); }
}

@media (max-width: 900px) {
  .left-panel {
    display: none;
  }
}
</style>
