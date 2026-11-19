import './index.css'

import { createApp } from 'vue'
import { FrappeUI, setConfig, frappeRequest } from 'frappe-ui'
import App from './App.vue'
import router from './router'

setConfig('resourceFetcher', frappeRequest)

// benches other than the first use another socket port (e.g. 9001), so take it from the server
createApp(App)
  .use(FrappeUI, { socketio: { port: Number(window.socketio_port) || 9000 } })
  .use(router)
  .mount('#app')
