import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'home', component: () => import('./pages/Home.vue') },
  { path: '/:project', redirect: (to) => ({ name: 'items', params: to.params }) },
  { path: '/:project/overview', name: 'overview', component: () => import('./pages/Overview.vue') },
  { path: '/:project/items', name: 'items', component: () => import('./pages/WorkItems.vue') },
  { path: '/:project/item/:id', name: 'item', component: () => import('./pages/ItemPage.vue') },
  { path: '/:project/pages/:page?', name: 'pages', component: () => import('./pages/Pages.vue') },
  { path: '/:project/settings', name: 'settings', component: () => import('./pages/Settings.vue') },
]

export default createRouter({ history: createWebHistory('/planner'), routes })
