import './index.css'
import { createApp } from 'vue'
import { setConfig, frappeRequest, resourcesPlugin } from 'frappe-ui'
import App from './App.vue'
import router from './router'
import { i18n, setLocale, initialLocale } from './i18n'

setConfig('resourceFetcher', frappeRequest)

const app = createApp(App)
app.use(router)
app.use(resourcesPlugin)
app.use(i18n)
setLocale(initialLocale())
app.mount('#app')
