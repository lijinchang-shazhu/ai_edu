<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api'
import AppIcon from '../components/AppIcon.vue'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import Card from '../components/ui/Card.vue'
import Markdown from '../components/Markdown.vue'
import { toast, toastError } from '../components/toast'

const stats = ref({
  participation: { avg: 0, trend: [] },
  accuracy: { avg: 0, trend: [] },
  error_points: [],
  knowledge_mastery: [],
})
const interactions = ref([])
const memories = ref([])
const updating = ref(false)
const updateStatus = ref('')
const report = ref('')
const showReport = ref(false)

const COMPONENT_LABELS = {
  choice: '单选题',
  judge: '判断题',
  drag: '拖拽排序',
  fill: '填空',
  match: '连线匹配',
  vote: '投票',
  explore: '探究',
  expand: '展开',
  submit: '提交',
}

function chartPaths(values, w = 300, h = 120) {
  const arr = values && values.length ? values : [0, 0]
  const max = Math.max(...arr, 1)
  const min = Math.min(...arr, 0)
  const range = max - min || 1
  const step = w / (arr.length - 1)
  const pts = arr.map((v, i) => {
    const x = +(i * step).toFixed(1)
    const y = +(h - ((v - min) / range) * (h - 24) - 12).toFixed(1)
    return { x, y }
  })
  const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
  const area = line + ` L${w},${h} L0,${h} Z`
  return { line, area }
}

const maxError = computed(() => Math.max(...(stats.value.error_points || []).map((e) => e.value), 1))
const maxMastery = computed(() => Math.max(...(stats.value.knowledge_mastery || []).map((e) => e.value), 1))

onMounted(async () => {
  try {
    const [s, i, m] = await Promise.all([
      api.learningStatistics(),
      api.learningInteractions(),
      api.learningMemories(),
    ])
    stats.value = s.data
    interactions.value = i.data.interactions
    memories.value = m.data.memories
  } catch (e) {}
})

async function updateMemory() {
  updating.value = true
  try {
    const res = await api.learningUpdate('示例课题')
    updateStatus.value = res.data.status
    toast('学情已回流更新记忆库')
    memories.value = (await api.learningMemories()).data.memories
  } catch (err) {
    toastError('回流失败：' + (err.response?.data?.detail || err.message))
  } finally {
    updating.value = false
  }
}

async function genReport() {
  try {
    const res = await api.learningReport('示例课题')
    report.value = res.data.report
    showReport.value = true
  } catch (err) {
    toastError('报告生成失败：' + (err.response?.data?.detail || err.message))
  }
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="page-title">学情看板</h1>
      <p class="muted mt-1">课堂交互数据可视化（Mock 演示数据），支持学情回流更新教师记忆库</p>
    </div>

    <div class="grid grid-cols-3 gap-4">
      <div class="card p-5">
        <div class="flex items-center gap-2 text-sm text-slate-500"><AppIcon name="chart" :size="16" /> 课堂参与度</div>
        <div class="mt-2 text-3xl font-bold text-primary-600">{{ stats.participation.avg }}%</div>
      </div>
      <div class="card p-5">
        <div class="flex items-center gap-2 text-sm text-slate-500"><AppIcon name="check" :size="16" /> 平均正确率</div>
        <div class="mt-2 text-3xl font-bold text-emerald-600">{{ stats.accuracy.avg }}%</div>
      </div>
      <div class="card p-5">
        <div class="flex items-center gap-2 text-sm text-slate-500"><AppIcon name="layers" :size="16" /> 已采集交互</div>
        <div class="mt-2 text-3xl font-bold text-slate-800">{{ interactions.length }}</div>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Card title="课堂参与度趋势">
        <svg viewBox="0 0 300 120" preserveAspectRatio="none" class="h-32 w-full">
          <defs>
            <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#6366f1" stop-opacity="0.28" />
              <stop offset="100%" stop-color="#6366f1" stop-opacity="0" />
            </linearGradient>
          </defs>
          <path :d="chartPaths(stats.participation.trend).area" fill="url(#g1)" />
          <path :d="chartPaths(stats.participation.trend).line" fill="none" stroke="#6366f1" stroke-width="2.5" stroke-linejoin="round" />
        </svg>
      </Card>
      <Card title="平均正确率趋势">
        <svg viewBox="0 0 300 120" preserveAspectRatio="none" class="h-32 w-full">
          <defs>
            <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#10b981" stop-opacity="0.28" />
              <stop offset="100%" stop-color="#10b981" stop-opacity="0" />
            </linearGradient>
          </defs>
          <path :d="chartPaths(stats.accuracy.trend).area" fill="url(#g2)" />
          <path :d="chartPaths(stats.accuracy.trend).line" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linejoin="round" />
        </svg>
      </Card>
    </div>

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Card title="学生易错点分布">
        <div class="space-y-3">
          <div v-for="e in stats.error_points" :key="e.name" class="flex items-center gap-3">
            <span class="w-20 shrink-0 text-xs text-slate-500">{{ e.name }}</span>
            <div class="h-6 flex-1 rounded bg-slate-100">
              <div
                class="flex h-6 items-center justify-end rounded bg-gradient-to-r from-rose-400 to-red-500 pr-2 text-xs font-semibold text-white"
                :style="{ width: (e.value / maxError) * 100 + '%' }"
              >
                {{ e.value }}
              </div>
            </div>
          </div>
        </div>
      </Card>
      <Card title="知识掌握度">
        <div class="space-y-3">
          <div v-for="k in stats.knowledge_mastery" :key="k.name" class="flex items-center gap-3">
            <span class="w-20 shrink-0 text-xs text-slate-500">{{ k.name }}</span>
            <div class="h-6 flex-1 rounded bg-slate-100">
              <div
                class="flex h-6 items-center justify-end rounded bg-gradient-to-r from-primary-400 to-violet-500 pr-2 text-xs font-semibold text-white"
                :style="{ width: (k.value / maxMastery) * 100 + '%' }"
              >
                {{ k.value }}%
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Card title="最近课堂交互记录">
        <div class="max-h-64 overflow-y-auto">
          <table class="w-full text-sm">
            <thead class="sticky top-0 bg-white text-left text-xs text-slate-400">
              <tr>
                <th class="py-2 font-medium">题目</th>
                <th class="py-2 font-medium">题型</th>
                <th class="py-2 font-medium">学生</th>
                <th class="py-2 font-medium">作答</th>
                <th class="py-2 font-medium">正误</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="r in interactions" :key="r.id">
                <td class="py-2 text-slate-600">{{ r.qid || '-' }}</td>
                <td class="py-2 text-slate-600">{{ COMPONENT_LABELS[r.component] || r.component }}</td>
                <td class="py-2 text-slate-600">{{ r.student }}</td>
                <td class="py-2 text-slate-600">{{ r.value }}</td>
                <td class="py-2">
                  <span :class="r.correct === 1 ? 'text-emerald-600' : r.correct === 0 ? 'text-red-500' : 'text-slate-400'">
                    {{ r.correct === 1 ? '✓' : r.correct === 0 ? '✗' : '-' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="记忆迭代记录">
        <div class="mb-4 flex items-center gap-3">
          <Button :disabled="updating" @click="updateMemory"><AppIcon name="refresh" :size="15" /> {{ updating ? '回流中…' : '模拟学情回流' }}</Button>
          <span v-if="updateStatus" class="text-xs text-slate-500">{{ updateStatus }}</span>
        </div>
        <div v-if="memories.length" class="max-h-64 space-y-2 overflow-y-auto">
          <div v-for="m in memories" :key="m.id" class="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div class="flex items-center gap-2">
              <Badge variant="warning">{{ m.error_type }}</Badge>
              <span class="text-sm font-medium text-slate-800">{{ m.knowledge_point }}</span>
            </div>
            <p class="mt-1 text-xs text-slate-500">{{ m.suggestion }}</p>
          </div>
        </div>
        <p v-else class="py-8 text-center text-sm text-slate-400">暂无记忆条目，点击上方按钮模拟回流</p>
      </Card>
    </div>

    <Card title="学情薄弱点报告">
      <div class="mb-4 flex items-center gap-3">
        <Button @click="genReport"><AppIcon name="file" :size="15" /> 生成报告</Button>
        <a
          v-if="showReport"
          :href="api.reportDownloadUrl('示例课题')"
          target="_blank"
          class="inline-flex items-center gap-2 rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          <AppIcon name="download" :size="15" /> 下载报告
        </a>
      </div>
      <div v-if="showReport" class="max-h-96 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-5">
        <Markdown :content="report" />
      </div>
      <p v-else class="text-sm text-slate-400">点击「生成报告」，自动汇总课堂交互、易错点与记忆迭代记录</p>
    </Card>
  </div>
</template>
