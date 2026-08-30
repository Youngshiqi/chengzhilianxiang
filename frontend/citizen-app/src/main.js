// ============================================================
// 城市设施报修 · 市民端 — 应用入口
// ============================================================
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './styles/variables.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
