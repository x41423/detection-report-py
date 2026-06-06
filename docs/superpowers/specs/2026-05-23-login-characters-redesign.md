# Login Page Characters Redesign

**Date:** 2026-05-23
**Status:** Draft

## Overview

Redesign the 4 login page animated characters (purple, black, orange, yellow) with a **cute and lively** style: new vivid colors, rich facial expressions, idle animations, interactive responses, floating bubble background, and success particles.

## Color Palette (B - 鲜明活泼)

| Character | Current | New      | Gradient (top→bottom)     |
|-----------|---------|----------|---------------------------|
| Purple    | #6c3ff5 | #8555ff  | #8555ff → #a78bfa         |
| Black     | #2d2d2d | #1a1a2e  | #1a1a2e → #3d3d5c         |
| Orange    | #ff9b6b | #ff7043  | #ff7043 → #ff9b6b         |
| Yellow    | #e8d754 | #ffd54f  | #ffd54f → #ffe082         |

All characters change from solid color to **vertical gradient** (180deg) for depth.

## Character Personalities (全量动态 C)

### Purple (紫色) — 傲娇/高冷 Tsundere
- Default: serene, half-lidded eyes, slight smirk
- Typing: rolls eyes, looks away dismissively
- Password visible: peeks with one eye, then quickly looks away
- Idle: occasional hair flip (body skew), slow blink
- Error: shocked wide eyes, mouth drops open

### Black (黑色) — 活泼弟弟 Lively Little Brother  
- Default: big bright eyes, slight smile
- Typing: eagerly watches the input, body leans forward
- Password visible: covers eyes with "hands" (遮罩)
- Idle: bounces slightly, blinks rapidly
- Error: frown, shakes head "tsk tsk"

### Orange (橙色) — 迷糊可爱 Ditsy Cute
- Default: big round eyes, mouth slightly open (surprised look)
- Typing: tilts head, pupils follow cursor
- Password visible: confused blink, head tilt
- Idle: gentle sway, random head tilt
- Error: exaggerated O-mouth, eyes wide

### Yellow (黄色) — 温柔知性 Gentle/Kind
- Default: soft smile (mouth line curves up)
- Typing: nods along gently, approving look
- Password visible: turns away politely
- Idle: gentle floating, slow blink with smile
- Error: concerned look, slight head shake

## Props Interface (AnimatedCharacters.vue)

```ts
interface AnimatedCharactersProps {
  isRegister?: boolean      // register mode vs login mode
  success?: boolean         // trigger success animation
  // existing props: modelValue (for typing detection), showPassword, email, etc.
}
```

## Interaction States

1. **Idle** — default state, characters follow mouse with unique styles
2. **Typing** — `modelValue.length > 0`, characters react (lean in, pupils track)
3. **Password visible** — `showPassword === true`, shy/hiding/peeking per personality
4. **Register mode** — `isRegister === true`, curious forward lean, "new friend?" expressions
5. **Error** — shock/sadness per personality, shake head animation (existing `triggerError`)
6. **Success** — `success === true`, celebratory bounce + colorful particle burst

## Animation System

### Continuous Animations
- **Floating idle:** each character gently bobs up/down (2-3px amplitude, different phases)
- **Random blinks:** every 3-5 seconds, independent per character
- **Random actions:** every 5-8 seconds, one character performs a personality action (head tilt, bounce, etc.)

### Interaction Animations
- **Mouse tracking:** pupils follow cursor (existing)
- **Typing rhythm:** pupils jitter slightly (±1px, 100ms intervals) during active typing
- **Body reaction:** `skewX` + `translateX` for leaning reactions
- **Eye shape changes:** blink height `2px` → normal height (existing, extended)
- **Mouth shape changes:** multiple configurations per character

### Character Interaction (Timed State Changes)
- Every 8-12s, one character performs a timed "glance" (eye direction change, body turn)
- Purple and Black occasionally glance at each other (both shift eye angles toward each other)
- Orange stares at form content with curiosity (eyes shift downward)
- Yellow nods along with positive typing feedback (gentle vertical body bounce)
- All interaction is timer-driven, not continuous detection

## Background Effects (B - 浮动气泡)

- 6-8 semi-transparent circular bubbles in the character background
- Colors match character palette (purple/orange/yellow tints)
- Slow upward drift + gentle horizontal sway (~15s cycle)
- Random sizes (20-60px diameter)
- Opacity 0.08-0.15, blur filter
- CSS `@keyframes` for base movement; JS controls `animation-play-state` via class toggle
- Bubbles pause on error state (add `.paused` class → `animation-play-state: paused`)

### Success Particles
- Trigger: parent component sets `success` prop to true (after auth API returns)
- Colored particle burst from each character's head
- 15-20 particles per character
- Colors: #8555ff, #ff7043, #ffd54f, #fff
- Particles rise up and fade out over 1.5s
- CSS `@keyframes` + absolute positioning (non-interfering layer)

## Mobile Adaptation

- At ≤900px, left panel (characters) is hidden (already implemented)
- No miniature character fallback needed (matching current behavior)
- `prefers-reduced-motion`: disable all animations except essential eye tracking

## Performance Considerations

- Use `transform` and `opacity` only for animations (GPU accelerated)
- Float animation uses CSS `@keyframes` where possible
- requestAnimationFrame for eye tracking only
- Pause RAF when page tab is not visible (`document.hidden` check)
- Bubble layer uses `will-change: transform` sparingly

## Files to Modify

- `frontend/src/components/AnimatedCharacters.vue` — major rewrite of style assignments, add CSS gradients, bubble layer, new expressions
- `frontend/src/views/AuthAccess.vue` — minor, pass auth state for success/failure triggers

## Constraints

- Must preserve existing `useAuth` composable integration
- Login/register tab switching must work with new animations
- All changes must pass `npm run typecheck` with 0 errors
- No external dependencies or libraries
