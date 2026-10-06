<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../api'
import AppIcon from '../components/AppIcon.vue'
import Badge from '../components/ui/Badge.vue'

const meta = ref({ mock_mode: true, mode: 'mock', kb_docs: 0, materials: 0, memories: 0 })
const showGuide = ref(true)
const display = ref({ kb: 0, materials: 0, memories: 0 })

function countUp(key, target) {
  const start = performance.now()
  const dur = 900
  function tick(now) {
    const p = Math.min(1, (now - start) / dur)
    display.value[key] = Math.round(target * (1 - Math.pow(1 - p, 3)))
    if (p < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

onMounted(async () => {
  try {
    meta.value = (await api.meta()).data
    countUp('kb', meta.value.kb_docs || 0)
    countUp('materials', meta.value.materials || 0)
    countUp('memories', meta.value.memories || 0)
  } catch (e) {}
})

const stats = computed(() => [
  { label: '知识库文档', value: display.value.kb, icon: 'book', to: '/knowledge' },
  { label: '教学素材', value: display.value.materials, icon: 'file', to: '/materials' },
  { label: '记忆条目', value: display.value.memories, icon: 'database', to: '/dashboard' },
])

const agents = [
  { name: '教学解析 Agent', desc: '解析材料 · 检索记忆 · 提取目标', icon: 'search' },
  { name: '教学校验 Agent', desc: '对标课标 · 纠错 · 过滤幻觉', icon: 'shield' },
  { name: '素材生成 Agent', desc: '教案 / 习题 / 话术 / 课件', icon: 'sparkles' },
  { name: '记忆更新 Agent', desc: '提炼易错点 · 回流记忆库', icon: 'refresh' },
]
</script>

<template>
  <div class="space-y-6">
    <!-- 演示引导 -->
    <div
      v-if="showGuide"
      class="animate-fade-up flex items-start gap-3 rounded-xl border border-primary-200 bg-primary-50 p-4"
    >
      <span class="mt-0.5 text-primary-600"><AppIcon name="sparkles" :size="18" /></span>
      <div class="flex-1 text-sm text-primary-800">
        <b>演示引导：</b>① 知识库上传教案 → ② 教学素材一键生成（可实时观察 AI 调用过程）→
        ③ 学情看板看数据回流 → ④ 随身师傅情景演练
      </div>
      <button class="text-primary-400 transition-colors hover:text-primary-600" @click="showGuide = false">
        <AppIcon name="x" :size="16" />
      </button>
    </div>

    <!-- Hero -->
    <section class="card animate-fade-up overflow-hidden">
      <div class="animate-gradient h-1.5 w-full bg-gradient-to-r from-primary-500 via-violet-500 to-cyan-400" />
      <div class="flex items-center justify-between p-8">
        <div>
          <h1 class="text-2xl font-bold leading-snug text-slate-900">
            基于教师终身教学记忆的<br />新教师范式化育人智能体系统
          </h1>
          <p class="mt-3 max-w-xl text-sm leading-relaxed text-slate-500">
            沉淀教师个人教学记忆，多智能体协作备课，同源生成教案、习题、演讲稿与交互式课件，
            采集课堂学情回流记忆库，形成「备课 — 授课 — 学情 — 迭代」育人闭环。
          </p>
          <div class="mt-5 flex gap-3">
            <RouterLink
              to="/materials"
              class="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-all hover:bg-primary-700 hover:shadow-md"
            >
              <AppIcon name="sparkles" :size="16" /> 开始备课
            </RouterLink>
            <RouterLink
              to="/chat"
              class="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            >
              <AppIcon name="message" :size="16" /> 咨询随身师傅
            </RouterLink>
          </div>
        </div>
        <div class="hidden animate-float items-center justify-center lg:flex">
          <div class="flex h-28 w-28 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-500 to-violet-600 text-white shadow-lg">
            <AppIcon name="school" :size="56" />
          </div>
        </div>
      </div>
    </section>

    <!-- 统计 -->
    <section class="grid grid-cols-3 gap-4">
      <RouterLink
        v-for="(s, i) in stats"
        :key="s.label"
        :to="s.to"
        class="card card-hover animate-fade-up p-5"
        :style="{ animationDelay: (i + 1) * 0.08 + 's' }"
      >
        <div class="flex items-center justify-between">
          <span class="text-primary-500"><AppIcon :name="s.icon" :size="22" /></span>
          <span class="text-3xl font-bold tabular-nums text-slate-900">{{ s.value }}</span>
        </div>
        <div class="mt-2 text-sm text-slate-500">{{ s.label }}</div>
      </RouterLink>
    </section>

    <!-- 多智能体流水线 -->
    <section class="animate-fade-up" style="animation-delay: 0.2s">
      <h2 class="mb-4 text-lg font-semibold text-slate-900">多智能体教学流水线</h2>
      <div class="grid grid-cols-4 gap-4">
        <div v-for="a in agents" :key="a.name" class="card card-hover p-5">
          <div class="flex items-center justify-between">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50 text-primary-600">
              <AppIcon :name="a.icon" :size="20" />
            </div>
            <span class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse-dot" title="运行中" />
          </div>
          <div class="mt-3 text-sm font-semibold text-slate-900">{{ a.name }}</div>
          <div class="mt-1 text-xs text-slate-500">{{ a.desc }}</div>
        </div>
      </div>
    </section>

    <!-- 闭环 -->
    <section class="card animate-fade-up p-6" style="animation-delay: 0.3s">
      <h2 class="mb-4 text-lg font-semibold text-slate-900">教学育人闭环</h2>
      <div class="flex flex-wrap items-center gap-3 text-sm">
        <Badge>智能备课</Badge><span class="text-slate-300">→</span>
        <Badge>交互课堂</Badge><span class="text-slate-300">→</span>
        <Badge>学情采集</Badge><span class="text-slate-300">→</span>
        <Badge>记忆迭代</Badge><span class="text-slate-300">↩</span>
        <span class="muted">数据回流更新教师个人教学记忆库</span>
      </div>
    </section>
  </div>
</template>
