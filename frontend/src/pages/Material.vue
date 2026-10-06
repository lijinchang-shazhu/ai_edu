<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api'
import AppIcon from '../components/AppIcon.vue'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import Card from '../components/ui/Card.vue'
import Input from '../components/ui/Input.vue'
import Textarea from '../components/ui/Textarea.vue'
import Markdown from '../components/Markdown.vue'
import { toast, toastError } from '../components/toast'

const title = ref('')
const subject = ref('示例学科')
const grade = ref('示例年级')
const docText = ref('')
const withLearning = ref(true)

const generating = ref(false)
const result = ref(null)
const activeTab = ref('lesson_plan')
const steps = ref([])

const savedMaterials = ref([])
const refineInstruction = ref('')
const refining = ref(false)
const editing = ref(false)
const editContent = ref('')
const versions = ref([])
const showVersions = ref(false)

const materialTabs = [
  { key: 'lesson_plan', label: '教案' },
  { key: 'exercises', label: '分层习题' },
  { key: 'speech', label: '演讲稿' },
  { key: 'parent_letter', label: '家校文案' },
  { key: 'reflection', label: '教学反思' },
  { key: 'micro_script', label: '微课脚本' },
  { key: 'interactive', label: '随堂互动练习' },
  { key: 'geometry_demo', label: '解析几何演示' },
]

const activeContent = computed(() => {
  const m = result.value?.materials?.[activeTab.value]
  return m ? m.content : ''
})

const design = computed(() => result.value?.design || {})
const validation = computed(() => result.value?.validation || {})

async function generate() {
  if (!title.value.trim()) {
    toastError('请先填写课题名称')
    return
  }
  generating.value = true
  steps.value = []
  result.value = null
  try {
    const payload = {
      doc_title: title.value.trim(),
      subject: subject.value || '示例学科',
      grade: grade.value || '示例年级',
      doc_text: docText.value.trim() || null,
      with_learning_data: withLearning.value,
    }
    const resp = await fetch('/api/workflow/run/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!resp.ok || !resp.body) throw new Error('stream unavailable')
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()
      for (const line of lines) {
        if (!line.startsWith('data:')) continue
        const chunk = line.slice(5).trim()
        if (chunk === '[DONE]') continue
        try {
          const ev = JSON.parse(chunk)
          if (ev.type === 'step') {
            steps.value.push(ev)
          } else if (ev.type === 'done' && ev.result) {
            result.value = ev.result
            activeTab.value = 'lesson_plan'
          }
        } catch (e) {}
      }
    }
    toast('全套教学素材生成完成')
    await loadSaved()
  } catch (err) {
    toastError('生成失败：' + (err.response?.data?.detail || err.message))
  } finally {
    generating.value = false
  }
}

async function refine() {
  if (!refineInstruction.value.trim() || !result.value) return
  refining.value = true
  try {
    const res = await api.refineMaterial(result.value.courseware.id, refineInstruction.value.trim())
    result.value.courseware.html = res.data.html
    refineInstruction.value = ''
    toast('课件已微调')
  } catch (err) {
    toastError('微调失败：' + (err.response?.data?.detail || err.message))
  } finally {
    refining.value = false
  }
}

async function startEdit() {
  const m = result.value?.materials?.[activeTab.value]
  if (!m) return
  editContent.value = m.content
  editing.value = true
  showVersions.value = false
  try {
    const res = await api.materialVersions(m.id)
    versions.value = res.data.versions
  } catch (e) {
    versions.value = []
  }
}

async function saveEdit() {
  const m = result.value?.materials?.[activeTab.value]
  if (!m) return
  try {
    await api.updateMaterial(m.id, editContent.value)
    m.content = editContent.value
    editing.value = false
    toast('已保存，历史版本已记录')
  } catch (err) {
    toastError('保存失败：' + (err.response?.data?.detail || err.message))
  }
}

function openFullscreen() {
  if (result.value) window.open(api.coursewareUrl(result.value.courseware.id), '_blank')
}

async function loadSaved() {
  try {
    const res = await api.materials()
    savedMaterials.value = res.data.materials
  } catch (e) {
    savedMaterials.value = []
  }
}

function typeLabel(type) {
  const map = {
    lesson_plan: '教案',
    exercises: '分层习题',
    speech: '演讲稿',
    parent_letter: '家校文案',
    reflection: '教学反思',
    micro_script: '微课脚本',
    courseware: '交互式课件',
  }
  return map[type] || type
}

onMounted(loadSaved)
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="page-title">教学素材生成</h1>
      <p class="muted mt-1">同源生成教案、习题、演讲稿、家校文案、反思、微课脚本、教学课件（讲课 PPT）与随堂互动练习</p>
    </div>

    <Card title="备课信息">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div>
          <label class="mb-1 block text-xs font-medium text-slate-500">课题名称 *</label>
          <Input v-model="title" placeholder="例如：一元二次方程" />
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-slate-500">学科</label>
          <Input v-model="subject" placeholder="例如：数学" />
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-slate-500">年级</label>
          <Input v-model="grade" placeholder="例如：初二" />
        </div>
      </div>
      <div class="mt-4">
        <label class="mb-1 block text-xs font-medium text-slate-500">教材 / 教案内容（可选，粘贴文本）</label>
        <Textarea v-model="docText" placeholder="可粘贴教材章节、教案初稿等材料…" :rows="4" />
      </div>
      <div class="mt-4 flex items-center gap-3">
        <label class="flex cursor-pointer items-center gap-2 text-sm text-slate-600">
          <input v-model="withLearning" type="checkbox" class="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500" />
          模拟课堂学情回流（触发记忆更新）
        </label>
        <Button size="lg" :disabled="generating" @click="generate">
          <AppIcon name="sparkles" :size="16" /> {{ generating ? '生成中，请稍候…' : '一键生成全套教学素材' }}
        </Button>
      </div>
    </Card>

    <Card v-if="steps.length || generating" title="AI 调用过程">
      <div class="space-y-2.5 font-mono text-[13px] leading-relaxed">
        <div v-if="generating && !steps.length" class="flex items-center gap-2 text-slate-400">
          <span class="inline-flex animate-spin text-primary-500"><AppIcon name="refresh" :size="14" /></span>
          正在连接大模型服务…
        </div>
        <div v-for="(s, i) in steps" :key="i" class="flex items-start gap-2.5">
          <span v-if="s.status === 'done'" class="mt-0.5 inline-flex text-emerald-500">
            <AppIcon name="check" :size="14" />
          </span>
          <span v-else class="mt-0.5 inline-flex animate-spin text-primary-500">
            <AppIcon name="refresh" :size="14" />
          </span>
          <div class="flex-1">
            <span class="font-medium text-slate-800">{{ s.agent }}</span>
            <span class="text-slate-500"> · {{ s.msg }}</span>
          </div>
        </div>
        <div v-if="generating" class="flex items-center gap-2 pt-1 text-xs font-sans text-primary-600">
          <span class="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-primary-500" />
          实时调用中…
        </div>
      </div>
    </Card>

    <template v-if="result">
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="教学解析结果">
          <div class="space-y-2 text-sm">
            <p><span class="font-medium text-slate-500">课题：</span>{{ design.title }}</p>
            <p><span class="font-medium text-slate-500">教学目标：</span>{{ design.objectives?.['知识与技能'] || design.objectives }}</p>
            <p><span class="font-medium text-slate-500">教学重点：</span>{{ (design.key_points || []).join('、') }}</p>
            <p><span class="font-medium text-slate-500">教学难点：</span>{{ (design.difficult_points || []).join('、') }}</p>
          </div>
        </Card>
        <Card title="教学校验结果">
          <div class="mb-3">
            <Badge :variant="validation.is_valid ? 'success' : 'danger'">
              {{ validation.is_valid ? '校验通过' : '存在待修改问题' }}
            </Badge>
          </div>
          <p class="mb-2 text-sm text-slate-600">{{ validation.standard_match }}</p>
          <ul v-if="(validation.issues || []).length" class="list-inside list-disc space-y-1 text-sm text-amber-700">
            <li v-for="(it, i) in validation.issues" :key="i">{{ it }}</li>
          </ul>
          <ul v-if="(validation.corrections || []).length" class="mt-2 list-inside list-disc space-y-1 text-sm text-emerald-700">
            <li v-for="(it, i) in validation.corrections" :key="i">{{ it }}</li>
          </ul>
          <p v-if="result.memory?.status" class="mt-3 flex items-center gap-1 text-xs text-slate-500">
            <AppIcon name="database" :size="14" /> {{ result.memory.status }}
          </p>
        </Card>
      </div>

      <Card title="生成的素材">
        <div class="mb-4 flex flex-wrap gap-2">
          <button
            v-for="t in materialTabs"
            :key="t.key"
            class="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
            :class="activeTab === t.key ? 'bg-primary-600 text-white shadow-sm' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
            @click="activeTab = t.key; editing = false"
          >
            {{ t.label }}
          </button>
        </div>
        <div v-if="['geometry_demo', 'interactive'].includes(activeTab)" class="overflow-hidden rounded-lg border border-slate-200">
          <iframe
            :src="api.coursewareUrl(result.materials[activeTab].id)"
            class="h-[520px] w-full"
            title="课件预览"
          />
        </div>
        <div v-else class="max-h-96 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-4">
          <Markdown v-if="!editing" :content="activeContent" />
          <Textarea v-else v-model="editContent" :rows="16" />
        </div>
        <div class="mt-4 flex flex-wrap gap-2">
          <a
            :href="api.downloadUrl(result.materials[activeTab]?.id)"
            target="_blank"
            class="inline-flex items-center gap-2 rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            <AppIcon name="download" :size="15" /> 下载
          </a>
          <Button v-if="!editing && !['geometry_demo', 'interactive'].includes(activeTab)" variant="outline" @click="startEdit"><AppIcon name="pencil" :size="15" /> 编辑</Button>
          <template v-else>
            <Button @click="saveEdit"><AppIcon name="check" :size="15" /> 保存</Button>
            <Button variant="outline" @click="editing = false"><AppIcon name="x" :size="15" /> 取消</Button>
            <Button variant="ghost" size="sm" @click="showVersions = !showVersions">
              <AppIcon name="layers" :size="14" /> 历史版本 ({{ versions.length }})
            </Button>
          </template>
        </div>

        <div v-if="editing && showVersions" class="mt-3 max-h-52 space-y-2 overflow-y-auto">
          <p v-if="!versions.length" class="text-xs text-slate-400">暂无历史版本</p>
          <div v-for="(v, i) in versions" :key="v.id" class="rounded-lg border border-slate-200 bg-white p-3 text-xs">
            <div class="mb-1 font-medium text-slate-500">版本 {{ versions.length - i }} · {{ v.created_at }}</div>
            <pre class="line-clamp-2 whitespace-pre-wrap font-sans text-slate-600">{{ v.content }}</pre>
          </div>
        </div>
      </Card>

      <Card title="讲课课件（投屏讲解）">
        <div class="mb-3 flex items-center gap-2">
          <Badge variant="success">数形结合 · 机理动画</Badge>
          <span class="text-xs text-slate-400">封面 → 分步讲解 → 数形结合函数图 → 抛体机理动画 → 小结，供上课投屏讲解</span>
          <div class="ml-auto flex gap-2">
            <a
              :href="api.coursewarePptxUrl(result.courseware.id)"
              target="_blank"
              class="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            >
              <AppIcon name="download" :size="14" /> 导出 PPT
            </a>
            <Button variant="outline" size="sm" @click="openFullscreen">
              <AppIcon name="external" :size="14" /> 全屏讲解
            </Button>
          </div>
        </div>
        <iframe
          :src="api.coursewareUrl(result.courseware.id)"
          class="h-[560px] w-full rounded-lg border border-slate-200"
          title="交互式课件预览"
        />
        <div class="mt-4 flex gap-2">
          <Input v-model="refineInstruction" placeholder="自然语言微调课件，例如：把主色调改成绿色、增加一道填空题" />
          <Button :disabled="refining" @click="refine"><AppIcon name="refresh" :size="15" /> {{ refining ? '微调中…' : '微调' }}</Button>
        </div>
      </Card>
    </template>

    <Card title="历史素材">
      <div v-if="savedMaterials.length" class="divide-y divide-slate-100">
        <div v-for="m in savedMaterials" :key="m.id" class="flex items-center justify-between py-3">
          <div class="flex items-center gap-3">
            <span class="text-primary-500"><AppIcon :name="m.type === 'courseware' ? 'layers' : 'file'" :size="20" /></span>
            <div>
              <div class="text-sm font-medium text-slate-800">{{ m.title }}</div>
              <div class="text-xs text-slate-400">{{ typeLabel(m.type) }} · {{ m.created_at }}</div>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <a v-if="m.type === 'courseware'" :href="api.coursewareUrl(m.id)" target="_blank" class="text-xs text-primary-600 hover:underline">预览</a>
            <a :href="api.downloadUrl(m.id)" target="_blank" class="text-xs text-slate-600 hover:underline">下载</a>
            <button class="text-xs text-red-500 hover:underline" @click="api.deleteMaterial(m.id).then(() => { loadSaved(); toast('已删除') })">删除</button>
          </div>
        </div>
      </div>
      <p v-else class="py-8 text-center text-sm text-slate-400">暂无历史素材</p>
    </Card>
  </div>
</template>
