# Login Page Characters Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign 4 login page animated characters with vivid gradients, personality-driven expressions, idle animations, floating bubble background, success particles, and character interaction.

**Architecture:** Single component `AnimatedCharacters.vue` handles all character state via a reactive `Styles` object. Parent `AuthAccess.vue` passes props (`isRegister`, `success`, existing `typing`/`showPassword`/`loginError`). All animations use CSS transforms/opacity for GPU acceleration.

**Tech Stack:** Vue 3 (`<script setup>`), CSS `@keyframes`, reactive state object, `requestAnimationFrame` for eye tracking.

---

### Task 1: Apply new vivid color palette + gradients

**Files:**
- Modify: `frontend/src/components/AnimatedCharacters.vue:440-645`

- [ ] **Step 1: Replace character background colors with gradient values**

In the `<style scoped>` section, change the `background` properties of `.char-purple`, `.char-black`, `.char-orange`, `.char-yellow`:

```
.char-purple {
  background: linear-gradient(180deg, #8555ff 0%, #a78bfa 100%);
}

.char-black {
  background: linear-gradient(180deg, #1a1a2e 0%, #3d3d5c 100%);
}

.char-orange {
  background: linear-gradient(180deg, #ff7043 0%, #ff9b6b 100%);
}

.char-yellow {
  background: linear-gradient(180deg, #ffd54f 0%, #ffe082 100%);
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend; npx vue-tsc -b
```

Expected: 0 errors.

---

### Task 2: Add idle floating animation

**Files:**
- Modify: `frontend/src/components/AnimatedCharacters.vue` (add CSS keyframes + styles)

- [ ] **Step 1: Add float keyframes**

```css
@keyframes floatPurple {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-4px); }
}
@keyframes floatBlack {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-3px); }
}
@keyframes floatOrange {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-5px); }
}
@keyframes floatYellow {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-2px); }
}
```

- [ ] **Step 2: Replace static `position: relative` on `.characters-scene` with animation classes**

Add inline animation on each `.character` via inline styles. In the reactive `s` object initial values and in `update()`, set an `animation` property on each character:

```js
// In s.purple initial: animation: 'floatPurple 4s ease-in-out infinite'
// Different durations per character: purple 4s, black 3.5s, orange 5s, yellow 4.5s
// Apply via s.purple = { ..., animation: 'floatPurple 4s ease-in-out infinite' }
```

Note: The existing `update()` sets `s.purple.transform` which will override the animation's transform. To fix: wrap the float in a parent `<div>` that stays outside the `transform` style, OR apply float animation to a separate wrapper element.

**Better approach:** Add a CSS class `.character-float` on each character wrapper div, and use `animation` via the CSS class. Remove the `animation` from inline styles entirely and use CSS for the float only.

Actually, the simplest approach: keep the character's `transform` for body skew/reactions, and add a wrapper `<div class="character-float">` around each character for the floating animation.

**Template change:** Wrap each `character div` in a float wrapper:

```html
<div class="character-float" :style="s.floatPurple">
  <div class="character char-purple" :style="s.purple">
    ...
  </div>
</div>
```

Add to `Styles` interface and `s` reactive:
```ts
floatPurple: Record<string, string>
floatBlack: Record<string, string>
floatOrange: Record<string, string>
floatYellow: Record<string, string>
```

Initial values:
```ts
floatPurple: { animation: 'floatPurple 4s ease-in-out infinite' },
floatBlack: { animation: 'floatBlack 3.5s ease-in-out infinite' },
floatOrange: { animation: 'floatOrange 5s ease-in-out infinite' },
floatYellow: { animation: 'floatYellow 4.5s ease-in-out infinite' },
```

- [ ] **Step 2: Verify build**

```bash
cd frontend; npx vue-tsc -b
```

Expected: 0 errors.

---

### Task 3: Add floating background bubbles

**Files:**
- Modify: `frontend/src/components/AnimatedCharacters.vue`

- [ ] **Step 1: Add bubble CSS keyframes**

```css
@keyframes bubbleUp {
  0% { transform: translateY(100vh) translateX(0px) scale(0.5); opacity: 0; }
  10% { opacity: 0.12; }
  90% { opacity: 0.08; }
  100% { transform: translateY(-100px) translateX(30px) scale(1); opacity: 0; }
}
@keyframes bubbleDrift {
  0%, 100% { transform: translateX(0px); }
  50% { transform: translateX(15px); }
}
.bubble { position: absolute; border-radius: 50%; pointer-events: none; will-change: transform; }
.bubble.paused { animation-play-state: paused; }
```

- [ ] **Step 2: Add bubble elements to template**

After the `</div>` closing `.characters-scene`, before the footer-links:

```html
<div class="bubble-layer" ref="bubbleLayerRef" :class="{ paused: isLoginError }">
  <div v-for="b in bubbles" :key="b.id" class="bubble"
    :style="{
      width: b.size + 'px', height: b.size + 'px',
      left: b.left + '%', bottom: b.bottom + '%',
      background: b.color,
      filter: 'blur(' + b.blur + 'px)',
      animationDelay: b.delay + 's',
      animationDuration: b.duration + 's',
    }">
  </div>
</div>
```

- [ ] **Step 3: Add bubble JS**

```ts
interface Bubble {
  id: number
  size: number
  left: number
  bottom: number
  color: string
  blur: number
  delay: number
  duration: number
}

const bubbleLayerRef = ref<HTMLElement | null>(null)
const bubbles: Bubble[] = []

function initBubbles() {
  const colors = ['rgba(133,85,255,0.5)', 'rgba(255,112,67,0.4)', 'rgba(255,213,79,0.3)']
  for (let i = 0; i < 8; i++) {
    bubbles.push({
      id: i,
      size: Math.random() * 40 + 20,
      left: Math.random() * 80 + 5,
      bottom: Math.random() * 60,
      color: colors[i % 3],
      blur: Math.random() * 4 + 2,
      delay: Math.random() * 12,
      duration: Math.random() * 8 + 10,
    })
  }
}
```

Call `initBubbles()` in `onMounted`.

- [ ] **Step 4: Add bubble-layer CSS**

```css
.bubble-layer {
  position: absolute;
  inset: 0;
  overflow: hidden;
  z-index: 1;
}
.bubble-layer.paused .bubble {
  animation-play-state: paused;
}
```

Use `bubbleUp` keyframe on all bubbles:
```css
.bubble {
  animation: bubbleUp linear infinite;
}
```

- [ ] **Step 5: Verify build**

```bash
cd frontend; npx vue-tsc -b
```

Expected: 0 errors.

---

### Task 4: Add `isRegister` and `success` props + wire AuthAccess

**Files:**
- Modify: `frontend/src/components/AnimatedCharacters.vue:61-66`
- Modify: `frontend/src/views/AuthAccess.vue:3-9`
- Modify: `frontend/src/views/AuthAccess.vue:254-303`

- [ ] **Step 1: Add new props to AnimatedCharacters**

```ts
const props = defineProps<{
  typing: boolean
  passwordFocused: boolean
  showPassword: boolean
  loginError: boolean
  isRegister?: boolean
  success?: boolean
}>()
```

- [ ] **Step 2: Expose `triggerSuccess` method**

```ts
function triggerSuccess() {
  // Will be implemented in Task 7
}
defineExpose({ triggerError, triggerSuccess })
```

- [ ] **Step 3: Pass `isRegister` from AuthAccess**

In `AuthAccess.vue` template:
```html
<AnimatedCharacters
  ref="charactersRef"
  :typing="formState.isTyping"
  :password-focused="formState.passwordFocused"
  :show-password="formState.showPassword"
  :login-error="formState.loginError"
  :is-register="isRegister"
/>
```

- [ ] **Step 4: Add success trigger in AuthAccess `onSubmit`**

After successful login (line 294) and successful register (line 271):

```ts
// Before navigation:
charactersRef.value?.triggerSuccess()
await new Promise(r => setTimeout(r, 1500)) // wait for animation
// then navigate
```

Modify both success paths:
- Line 271: After `ElMessage.success('注册成功，请登录')`, add `charactersRef.value?.triggerSuccess(); await new Promise(r => setTimeout(r, 1500))` before `router.push`
- Line 294: After `ElMessage.success('登录成功')`, add `charactersRef.value?.triggerSuccess(); await new Promise(r => setTimeout(r, 1500))` before `redirectAfterLogin()`

Pending login response (line 289-292): no success animation, only navigate.

- [ ] **Step 5: Verify build**

```bash
cd frontend; npx vue-tsc -b
```

Expected: 0 errors.

---

### Task 5: Rewrite update() for personality-driven expressions

**Files:**
- Modify: `frontend/src/components/AnimatedCharacters.vue:164-327`

- [ ] **Step 1: Add state variables for new behaviors**

```ts
let isRegisterMode = false
let isSuccess = false
// Keep existing: isLoginError, isLookingAtEachOther, isPurpleBlinking, isBlackBlinking, isPurplePeeking
```

- [ ] **Step 2: Watch new props**

```ts
watch(() => props.isRegister, (val) => { isRegisterMode = !!val; update() })
watch(() => props.success, (val) => { if (val) triggerSuccess() })
```

- [ ] **Step 3: Add `isLookingAway` condition for register mode**

The current logic checks `isLookingAway` for `passwordFocused && !showPwd`. Add register mode as another branch:

```
State priority (from update() if-else chain):
1. isLoginError (error response)
2. isSuccess (success flash)
3. isLookingAway (password focused, no show)
4. showPwd (password visible)
5. isLookingAtEachOther (typing)
6. isRegisterMode (register tab)
7. default (idle + mouse tracking)
```

- [ ] **Step 4: Implement personality expressions per state**

**Purple (傲娇):**
- Default (idle): `s.purpleEyes = { left: '45px', top: '40px' }`, pupils mostly centered, slight upward angle
- isLookingAway: strong eye roll `s.purpleEyes = { left: '15px', top: '30px' }`, pupils far left
- showPwd: peek animation (existing)
- isLookingAtEachOther: glance right at black `s.purpleEyes = { left: '55px', top: '45px' }`
- isRegisterMode: dismissive look away `s.purpleEyes = { left: '20px', top: '30px' }`
- isLoginError: already done (shock)

**Black (活泼弟弟):**
- Default: big eyes, centered
- isLookingAway: curious lean forward `s.black = { transform: 'skewX(8deg) translateX(10px)' }`
- showPwd: cover eyes (add a solid element overlay, or just close eyes: height 2px)
- isLookingAtEachOther: glance left at purple
- isRegisterMode: excited bounce `s.black = { ... }` with bigger eyes
- isLoginError: already done (frown, head shake)

**Orange (迷糊可爱):**
- Default: big round eyes, O-mouth visible (change from current behavior where it's hidden)
  - Actually per spec: mouth "slightly open (surprised look)" — make `.orange-mouth` always visible with `opacity: 0.6`, full opacity on error
- isLookingAway: tilt head, confused expression
- showPwd: confused blink
- isRegisterMode: head tilt + bigger eyes
- isLoginError: already done (exaggerated O-mouth)

**Yellow (温柔知性):**
- Default: soft curved mouth line (change `.yellow-mouth` from straight line to slight curve)
  - Use a `border-radius` change or a small rotation to make it a gentle smile
- isLookingAway: concerned, turns away slightly
- showPwd: polite turn away
- isRegisterMode: warm smile (bigger curve)
- isLoginError: concerned look

Implementation approach: Extend the if-else chain in `update()` with a new `isRegisterMode` branch after `isLookingAtEachOther` and before the default branch. Each branch sets all character styles.

- [ ] **Step 5: Verify build**

```bash
cd frontend; npx vue-tsc -b
```

Expected: 0 errors. (No compile errors since all changes are JS logic within an existing function.)

---

### Task 6: Add character interaction timer

**Files:**
- Modify: `frontend/src/components/AnimatedCharacters.vue`

- [ ] **Step 1: Add interaction state timers**

```ts
let interactionTimer: ReturnType<typeof setTimeout> | null = null
let characterInteraction = '' // '', 'purpleGlance', 'blackWave', 'orangeTilt', 'yellowNod'
```

- [ ] **Step 2: Implement `scheduleInteraction` function**

```ts
function scheduleInteraction() {
  interactionTimer = setTimeout(() => {
    const actions = ['purpleGlance', 'blackWave', 'orangeTilt', 'yellowNod']
    characterInteraction = actions[Math.floor(Math.random() * actions.length)]
    update()
    // Revert after 2s
    interactionTimer = setTimeout(() => {
      characterInteraction = ''
      update()
      scheduleInteraction()
    }, 2000)
  }, Math.random() * 4000 + 8000) // every 8-12s
}
```

- [ ] **Step 3: Use `characterInteraction` in update()**

In each character's default (idle) branch, check `characterInteraction`:
- `'purpleGlance'`: set purple eyes to glance right (toward black)
- `'blackWave'`: minor body bounce for black
- `'orangeTilt'`: add head tilt rotation to orange
- `'yellowNod'`: subtle vertical body bounce

```js
// In default branch for purple:
if (characterInteraction === 'purpleGlance') {
  s.purpleEyes = { left: '60px', top: '40px' }
  s.purplePupilL = { transform: 'translate(4px, 0px)' }
  s.purplePupilR = { transform: 'translate(4px, 0px)' }
}
```

- [ ] **Step 4: Wire into lifecycle**

Add `scheduleInteraction()` call in `onMounted`, and clear in `onUnmounted`.

- [ ] **Step 5: Verify build**

```bash
cd frontend; npx vue-tsc -b
```

Expected: 0 errors.

---

### Task 7: Add success particles animation

**Files:**
- Modify: `frontend/src/components/AnimatedCharacters.vue`

- [ ] **Step 1: Add particle CSS**

```css
@keyframes particleBurst {
  0% { transform: translateY(0) scale(1); opacity: 1; }
  100% { transform: translateY(-120px) translateX(var(--dx)) scale(0); opacity: 0; }
}
.particle-container { position: absolute; inset: 0; pointer-events: none; z-index: 20; }
.particle {
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: particleBurst 1.5s ease-out forwards;
}
```

- [ ] **Step 2: Add `triggerSuccess` implementation**

```ts
let successTimer: ReturnType<typeof setTimeout> | null = null

function triggerSuccess() {
  if (successTimer) clearTimeout(successTimer)
  isSuccess = true
  update()
  successTimer = setTimeout(() => {
    isSuccess = false
    update()
  }, 2000)
}
```

- [ ] **Step 3: Add particles template + state**

Add to template (inside `.characters-scene`):
```html
<div v-if="showParticles" class="particle-container">
  <div v-for="p in particles" :key="p.id" class="particle"
    :style="{
      left: p.x + '%',
      top: p.y + '%',
      background: p.color,
      width: p.size + 'px',
      height: p.size + 'px',
      '--dx': p.dx + 'px',
      animationDelay: p.delay + 's',
    }">
  </div>
</div>
```

State:
```ts
const showParticles = ref(false)
const particles = ref<Array<{id:number,x:number,y:number,color:string,size:number,dx:number,delay:number}>>([])
```

Generate particles in `triggerSuccess`:
```ts
const colors = ['#8555ff', '#ff7043', '#ffd54f', '#ffffff']
const newParticles = []
for (let i = 0; i < 20; i++) {
  newParticles.push({
    id: i,
    x: 15 + Math.random() * 70, // spread across scene
    y: 30 + Math.random() * 30, // character head area
    color: colors[i % 4],
    size: Math.random() * 6 + 4,
    dx: (Math.random() - 0.5) * 80,
    delay: Math.random() * 0.3,
  })
}
particles.value = newParticles
showParticles.value = true
setTimeout(() => { showParticles.value = false; particles.value = [] }, 2000)
```

- [ ] **Step 4: Verify build**

```bash
cd frontend; npx vue-tsc -b
```

Expected: 0 errors.

---

### Task 8: Performance optimization

**Files:**
- Modify: `frontend/src/components/AnimatedCharacters.vue`

- [ ] **Step 1: Add `document.hidden` check to pause RAF**

```ts
function onVisibilityChange() {
  if (document.hidden) {
    // Pause: stop blink timers, clear interaction timer
    if (purpleBlinkTimer) clearTimeout(purpleBlinkTimer)
    if (blackBlinkTimer) clearTimeout(blackBlinkTimer)
    if (interactionTimer) clearTimeout(interactionTimer)
  } else {
    // Resume
    scheduleBlinkPurple()
    scheduleBlinkBlack()
    scheduleInteraction()
    update()
  }
}
```

Add listener in `onMounted`:
```ts
document.addEventListener('visibilitychange', onVisibilityChange)
```

Remove in `onUnmounted`:
```ts
document.removeEventListener('visibilitychange', onVisibilityChange)
```

- [ ] **Step 2: Add `prefers-reduced-motion` media query**

```css
@media (prefers-reduced-motion: reduce) {
  .character-float { animation: none !important; }
  .bubble-layer { display: none; }
  .particle-container { display: none; }
}
```

- [ ] **Step 3: Verify build**

```bash
cd frontend; npx vue-tsc -b
```

Expected: 0 errors.

---

### Task 9: Final integration + typecheck

- [ ] **Step 1: Full typecheck**

```bash
cd frontend; npx vue-tsc -b
```

- [ ] **Step 2: Full build**

```bash
cd frontend; npx vite build
```

Expected: Build succeeds.

- [ ] **Step 3: Verify in browser**
- Login page loads without console errors
- Characters show new gradient colors
- Characters float gently
- Bubbles rise in background
- Mouse tracking works for all 4 characters
- Typing triggers expressions
- Password visible triggers expressions
- Error shakes heads
- Register mode: characters react
- Success: particles burst

- [ ] **Step 4: Quick cleanup**
- Remove any leftover `console.log` statements
- Ensure all Chinese comments are appropriate
