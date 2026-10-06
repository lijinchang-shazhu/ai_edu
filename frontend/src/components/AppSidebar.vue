<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import api from '../api'
import AppIcon from './AppIcon.vue'
import Badge from './ui/Badge.vue'

const route = useRoute()
const meta = ref({ mock_mode: true, mode: 'mock' })

onMounted(async () => {
  try {
    meta.value = (await api.meta()).data
  } catch (e) {
    /* 后端未启动时静默 */
  }
})

const navs = [
  { path: '/', label: '首页', icon: 'home' },
  { path: '/knowledge', label: '知识库', icon: 'book' },
  { path: '/chat', label: 'AI 问答', icon: 'message' },
  { path: '/materials', label: '教学素材', icon: 'file' },
  { path: '/dashboard', label: '学情看板', icon: 'chart' },
]
</script>

<template>
  <aside class="flex h-full w-60 flex-col border-r border-slate-200 bg-white">
    <RouterLink to="/" class="flex items-center gap-3 px-5 py-6">
      <div
        class="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50 text-primary-600"
      >
        <AppIcon name="school" :size="22" />
      </div>
      <div>
        <div class="text-sm font-semibold leading-tight text-slate-900">范式化育人智能体</div>
        <div class="text-xs text-slate-400">教师终身教学记忆</div>
      </div>
    </RouterLink>

    <nav class="flex-1 space-y-1 px-3">
      <RouterLink
        v-for="n in navs"
        :key="n.path"
        :to="n.path"
        class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors"
        :class="
          route.path === n.path
            ? 'bg-primary-50 text-primary-700'
            : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
        "
      >
        <AppIcon :name="n.icon" :size="18" />
        <span>{{ n.label }}</span>
      </RouterLink>
    </nav>

    <div class="border-t border-slate-100 px-5 py-4">
      <Badge :variant="meta.mock_mode ? 'secondary' : 'success'">
        {{ meta.mock_mode ? '本地示例' : '真实大模型' }}
      </Badge>
    </div>
  </aside>
</template>
