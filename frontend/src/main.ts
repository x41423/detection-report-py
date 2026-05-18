import { createApp } from 'vue'
import 'element-plus/dist/index.css'
import api from './api/client'
import { installAuthInterceptors, setAuthSessionExpiredCallback } from './api/authInterceptors'
import router from './router'
import App from './App.vue'
import './style.css'

installAuthInterceptors(api)
setAuthSessionExpiredCallback(() => {
  const currentRoute = router.currentRoute.value
  if (currentRoute.path === '/login' || currentRoute.path === '/register') {
    return
  }
  void router.replace({
    path: '/login',
    query: {
      redirect: currentRoute.fullPath || '/',
    },
  })
})

const app = createApp(App)
app.use(router)
app.mount('#app')
