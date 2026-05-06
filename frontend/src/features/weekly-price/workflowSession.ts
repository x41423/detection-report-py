const ALIAS_REVISION_KEY = 'weekly-price:alias-revision'

function canUseStorage() {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'
}

export function getWeeklyPriceAliasRevision() {
  if (!canUseStorage()) return ''

  try {
    return window.localStorage.getItem(ALIAS_REVISION_KEY) || ''
  } catch {
    return ''
  }
}

export function setWeeklyPriceAliasRevision(revision: string) {
  if (!canUseStorage()) return revision

  try {
    if (revision) window.localStorage.setItem(ALIAS_REVISION_KEY, revision)
    else window.localStorage.removeItem(ALIAS_REVISION_KEY)
  } catch {
    // Ignore storage failures and keep the in-memory flow working.
  }

  return revision
}

export function markWeeklyPriceAliasRevisionChanged() {
  return setWeeklyPriceAliasRevision(`${Date.now()}`)
}

export function watchWeeklyPriceAliasRevision(onChange: (revision: string) => void) {
  if (typeof window === 'undefined') {
    return () => {}
  }

  const handleStorage = (event: StorageEvent) => {
    if (event.storageArea !== window.localStorage) return
    if (event.key !== ALIAS_REVISION_KEY) return
    onChange(event.newValue || '')
  }

  window.addEventListener('storage', handleStorage)
  return () => {
    window.removeEventListener('storage', handleStorage)
  }
}
