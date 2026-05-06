import api from './client'

export function getConfig() {
  return api.get('/api/config/')
}

export function updateConfig(updates: Record<string, unknown>) {
  return api.put('/api/config/', { updates })
}
