import { createApp } from 'vue'
import 'element-plus/dist/index.css'
import api from './api/client'
import { installAuthInterceptors } from './api/authInterceptors'
import router from './router'
import App from './App.vue'
import './style.css'

installAuthInterceptors(api)

const app = createApp(App)
app.use(router)
app.mount('#app')
