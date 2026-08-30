// ============================================================
// 城市设施报修 · 维修工H5应用入口
// ============================================================
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router/index'
import './styles/variables.css'

const app = createApp(App)
app.use(router)
app.use(createPinia())
app.mount('#app')
