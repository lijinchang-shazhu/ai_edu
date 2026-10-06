import { createRouter, createWebHashHistory } from 'vue-router'
import Home from '../pages/Home.vue'
import KnowledgeBase from '../pages/KnowledgeBase.vue'
import Chat from '../pages/Chat.vue'
import Material from '../pages/Material.vue'
import Dashboard from '../pages/Dashboard.vue'

const routes = [
  { path: '/', name: 'home', component: Home, meta: { title: '首页' } },
  { path: '/knowledge', name: 'knowledge', component: KnowledgeBase, meta: { title: '知识库' } },
  { path: '/chat', name: 'chat', component: Chat, meta: { title: '随身师傅' } },
  { path: '/materials', name: 'materials', component: Material, meta: { title: '教学素材' } },
  { path: '/dashboard', name: 'dashboard', component: Dashboard, meta: { title: '学情看板' } },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
