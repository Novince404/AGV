import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router'
import { installLegacyApiFetchDefaults } from './services/apiClient'
import './styles/tokens.css'

installLegacyApiFetchDefaults()

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
