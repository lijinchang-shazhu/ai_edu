<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import api from '../api'
import AppIcon from '../components/AppIcon.vue'
import Button from '../components/ui/Button.vue'
import { toast, toastError } from '../components/toast'
import { currentTeacher } from '../components/teacher'

const messages = ref([])
const input = ref('')
const sending = ref(false)
const boxRef = ref(null)

const tree = ref({ private: [], public: [] })
const openSec = ref({ private: true, public: true })
const refTarget = ref(null) // { type: 'doc'|'collection', id?, key?, label }
const sessionId = ref(Math.random().toString(36).slice(2, 10))
const favorites = ref(JSON.parse(localStorage.getItem('fav') || '[]'))
const showFavOnly = ref(false)
const showTree = ref(true)
const showScenarios = ref(true)

const visibleMessages = computed(() =>
  showFavOnly.value ? messages.value.filter((m) => m.fav) : messages.value
)

// 会话历史
const sessions = ref(JSON.parse(localStorage.getItem('sessions') || '[]'))
const showHistory = ref(false)

// 自定义场景
const customScenarios = ref(JSON.parse(localStorage.getItem('customScenarios') || '[]'))
const showScenarioForm = ref(false)
const newScenarioName = ref('')
const newScenarioPrompt = ref('')
const allScenarios = computed(() => [...scenarios, ...customScenarios.value])

// @ 引用联想
const allRefs = computed(() => {
  const refs = [
    { type: 'collection', key: 'private', label: '教师私有记忆库' },
    { type: 'collection', key: 'public', label: '公共课标知识库' },
  ]
  for (const d of [...tree.value.private, ...tree.value.public]) {
    refs.push({ type: 'doc', id: d.id, label: d.title })
  }
  return refs
})

const mentionMatches = computed(() => {
  const q = (input.value.split('@').pop() || '').trim()
  if (!q) return allRefs.value.slice(0, 8)
  return allRefs.value.filter((r) => r.label.includes(q)).slice(0, 8)
})

function pickMention(r) {
  if (r.type === 'doc') {
    refTarget.value = { type: 'doc', id: r.id, label: '《' + r.label + '》' }
  } else {
    refTarget.value = { type: 'collection', key: r.key, label: r.label }
  }
  input.value = input.value.replace(/@[^\s]*$/, '').trim()
  toast('已引用：' + refTarget.value.label)
}

const GREETING =
  '你好，我是你的「AI 问答」助手。\n\n· 直接提问：我会结合你的教学记忆与名师经验作答\n· @ 引用：在左侧点选某个文档或分类，进行针对性问答\n· 情景演练：点击上方按钮进行课堂 / 突发 / 家校模拟'

const scenarios = [
  {
    label: '课堂控场',
    prompt:
      '请开启情境模拟演练。情景：上课时有两名学生大声喧哗、影响课堂秩序。请先让我以新教师身份给出应对，然后你点评并示范更专业的控场话术。',
  },
  {
    label: '突发问题',
    prompt:
      '请开启情境模拟演练。情景：课堂上突然有一名学生身体不适。请先让我以新教师身份应对，然后你点评并示范正确处理流程。',
  },
  {
    label: '家校沟通',
    prompt:
      '请开启情境模拟演练。情景：一名学生近期成绩下滑，家长来电质疑教师。请先让我以新教师身份沟通，然后你点评并示范更专业的沟通话术。',
  },
  {
    label: '学生走神',
    prompt:
      '请开启情境模拟演练。情景：课堂上多名学生注意力不集中、走神或做小动作。请先让我以新教师身份应对，然后你点评并示范更专业的引导方法。',
  },
  {
    label: '学生冲突',
    prompt:
      '请开启情境模拟演练。情景：两名学生在课堂上发生口角冲突。请先让我以新教师身份处置，然后你点评并示范正确处理流程。',
  },
  {
    label: '学生顶撞',
    prompt:
      '请开启情境模拟演练。情景：一名学生当众顶撞、质疑老师的教学。请先让我以新教师身份回应，然后你点评并示范更专业的应对话术。',
  },
  {
    label: '不交作业',
    prompt:
      '请开启情境模拟演练。情景：一名学生多次不交作业、态度敷衍。请先让我以新教师身份沟通，然后你点评并示范处理建议。',
  },
]

onMounted(async () => {
  messages.value.push({ role: 'assistant', content: GREETING })
  try {
    const res = await api.kbList(null, currentTeacher.value)
    const docs = res.data.documents || []
    tree.value.private = docs.filter((d) => d.collection !== 'public')
    tree.value.public = docs.filter((d) => d.collection === 'public')
  } catch (e) {}
})

function selectRef(payload) {
  refTarget.value = payload
  toast(`已引用：${payload.label}`)
}

function clearRef() {
  refTarget.value = null
}

function saveCurrentSession() {
  const userMsgs = messages.value.filter((m) => m.role === 'user')
  if (!userMsgs.length) return
  const title = userMsgs[0].content.slice(0, 24)
  sessions.value.unshift({
    id: sessionId.value,
    title,
    updatedAt: new Date().toLocaleString('zh-CN'),
    count: messages.value.length,
    messages: JSON.parse(JSON.stringify(messages.value)),
  })
  localStorage.setItem('sessions', JSON.stringify(sessions.value))
}

function newChat() {
  saveCurrentSession()
  messages.value = [{ role: 'assistant', content: GREETING }]
  refTarget.value = null
  sessionId.value = Math.random().toString(36).slice(2, 10)
  showHistory.value = false
  toast('已开启新对话')
}

function loadSession(s) {
  saveCurrentSession()
  messages.value = JSON.parse(JSON.stringify(s.messages))
  sessionId.value = s.id
  showHistory.value = false
  toast('已加载会话')
}

function deleteSession(id) {
  sessions.value = sessions.value.filter((s) => s.id !== id)
  localStorage.setItem('sessions', JSON.stringify(sessions.value))
}

function addScenario() {
  if (!newScenarioName.value.trim() || !newScenarioPrompt.value.trim()) {
    toastError('请填写场景名称和描述')
    return
  }
  customScenarios.value.push({
    label: newScenarioName.value.trim(),
    prompt: newScenarioPrompt.value.trim(),
  })
  localStorage.setItem('customScenarios', JSON.stringify(customScenarios.value))
  newScenarioName.value = ''
  newScenarioPrompt.value = ''
  showScenarioForm.value = false
  toast('自定义场景已添加')
}

async function send(preset) {
  const text = (preset ?? input.value).trim()
  if (!text || sending.value) return
  messages.value.push({ role: 'user', content: text, ref: refTarget.value?.label || '' })
  input.value = ''
  sending.value = true
  scroll()
  const history = messages.value.slice(0, -1).map((m) => ({ role: m.role, content: m.content }))
  const ai = { role: 'assistant', content: '', retry: text }
  messages.value.push(ai)
  try {
    let url, payload
    if (refTarget.value) {
      url = '/api/kb/chat/stream'
      payload = { message: text, session_id: sessionId.value, teacher: currentTeacher.value }
      if (refTarget.value.type === 'doc') payload.doc_id = refTarget.value.id
      else payload.collection = refTarget.value.key
    } else {
      url = '/api/chat/stream'
      payload = { message: text, history, session_id: sessionId.value, teacher: currentTeacher.value }
    }
    const meta = await streamTo(ai, url, payload)
    if (meta?.scope) ai.scope = meta.scope
  } catch (err) {
    if (!ai.content) {
      ai.content = '请求失败：' + (err.response?.data?.detail || err.message)
      ai.error = true
    }
  } finally {
    sending.value = false
    scroll()
  }
}

async function streamTo(ai, url, payload) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!resp.ok || !resp.body) throw new Error('stream unavailable')
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let meta = {}
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
        const j = JSON.parse(chunk)
        if (j.delta) {
          ai.content += j.delta
          scroll()
        }
        if (j.type === 'done') meta = { scope: j.scope, sources: j.sources }
      } catch (e) {}
    }
  }
  if (!ai.content) throw new Error('empty stream')
  return meta
}

async function copyMsg(m) {
  try {
    await navigator.clipboard.writeText(m.content)
    toast('已复制到剪贴板')
  } catch (e) {
    toastError('复制失败')
  }
}

function toggleFav(m) {
  m.fav = !m.fav
  if (m.fav) {
    if (!favorites.value.includes(m.content)) favorites.value.push(m.content)
  } else {
    favorites.value = favorites.value.filter((c) => c !== m.content)
  }
  localStorage.setItem('fav', JSON.stringify(favorites.value))
  toast(m.fav ? '已收藏' : '已取消收藏')
}

async function toDoc(m) {
  try {
    const title = '问答记录 · ' + m.content.slice(0, 20).replace(/\n/g, ' ')
    await api.saveMaterial({ title, content: m.content, type: 'note' })
    toast('已转为文档，可在「教学素材」中查看')
  } catch (err) {
    toastError('保存失败：' + (err.response?.data?.detail || err.message))
  }
}

async function scroll() {
  await nextTick()
  if (boxRef.value) boxRef.value.scrollTop = boxRef.value.scrollHeight
}
</script>

<template>
  <div class="flex h-[calc(100vh-5rem)] flex-col">
    <div class="mb-3 flex items-center justify-between">
      <div>
        <h1 class="page-title">AI 问答</h1>
        <p class="muted mt-1">基于知识库的智能问答 · 左侧点选文档/分类可 @ 引用，或直接咨询随身师傅</p>
      </div>
      <div class="flex gap-2">
        <Button variant="ghost" size="sm" @click="showHistory = true"><AppIcon name="layers" :size="14" /> 历史</Button>
        <Button variant="ghost" size="sm" :class="showFavOnly ? 'text-amber-500' : ''" @click="showFavOnly = !showFavOnly">
          收藏 ({{ favorites.length }})
        </Button>
        <Button variant="outline" size="sm" @click="newChat"><AppIcon name="plus" :size="14" /> 新对话</Button>
      </div>
    </div>

    <div class="mb-3 flex flex-wrap items-center gap-2">
      <button
        class="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-600 transition-colors hover:border-primary-400 hover:text-primary-700"
        @click="showTree = !showTree"
      >
        <AppIcon name="book" :size="15" /> {{ showTree ? '隐藏知识库' : '显示知识库' }}
      </button>
      <span
        v-if="refTarget"
        class="inline-flex items-center gap-1.5 rounded-full bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700"
      >
        <AppIcon name="target" :size="13" /> 引用：{{ refTarget.label }}
        <button class="text-primary-400 hover:text-primary-600" @click="clearRef"><AppIcon name="x" :size="12" /></button>
      </span>
      <button
        class="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-600 transition-colors hover:border-primary-400 hover:text-primary-700"
        @click="showScenarios = !showScenarios"
      >
        <AppIcon name="target" :size="15" /> 情景演练合集 ({{ allScenarios.length }})
        <span class="text-slate-400">{{ showScenarios ? '▾' : '▸' }}</span>
      </button>
    </div>

    <div v-if="showScenarios" class="mb-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
      <div class="flex flex-wrap gap-2">
        <button
          v-for="s in allScenarios"
          :key="s.label"
          class="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-600 transition-colors hover:border-primary-400 hover:text-primary-700"
          @click="send(s.prompt)"
        >
          <AppIcon name="target" :size="15" /> {{ s.label }}
        </button>
        <button
          class="inline-flex items-center gap-2 rounded-lg border border-dashed border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-500 transition-colors hover:border-primary-400 hover:text-primary-700"
          @click="showScenarioForm = !showScenarioForm"
        >
          <AppIcon name="plus" :size="15" /> 自定义场景
        </button>
      </div>
      <div v-if="showScenarioForm" class="mt-2 flex flex-wrap gap-2">
        <input
          v-model="newScenarioName"
          placeholder="场景名称（如：公开课怯场）"
          class="h-9 w-40 rounded-lg border border-slate-300 bg-white px-2 text-sm focus:border-primary-500 focus:outline-none"
        />
        <input
          v-model="newScenarioPrompt"
          placeholder="场景描述 / 演练要求"
          class="h-9 min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-2 text-sm focus:border-primary-500 focus:outline-none"
        />
        <Button size="sm" @click="addScenario">添加</Button>
      </div>
    </div>

    <div class="flex flex-1 gap-4 overflow-hidden">
      <!-- 左侧知识库树 -->
      <aside v-if="showTree" class="w-64 shrink-0 overflow-y-auto rounded-xl border border-slate-200 bg-white p-3">
        <div class="mb-2 px-1 text-xs font-semibold text-slate-400">知识库 · 点击引用</div>

        <div class="mb-1">
          <button
            class="flex w-full items-center justify-between rounded-lg px-2 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            @click="openSec.private = !openSec.private"
          >
            <span class="flex items-center gap-1.5"><AppIcon name="database" :size="14" /> 教师私有记忆库</span>
            <span class="text-slate-400">{{ openSec.private ? '▾' : '▸' }}</span>
          </button>
          <div v-if="openSec.private" class="pl-4">
            <div
              class="cursor-pointer rounded px-2 py-1 text-xs text-primary-600 hover:bg-primary-50"
              @click="selectRef({ type: 'collection', key: 'private', label: '教师私有记忆库' })"
            >
              @ 整个分类
            </div>
            <div
              v-for="d in tree.private"
              :key="d.id"
              class="cursor-pointer truncate rounded px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
              @click="selectRef({ type: 'doc', id: d.id, label: '《' + d.title + '》' })"
            >
              {{ d.title }}
            </div>
            <p v-if="!tree.private.length" class="px-2 py-1 text-xs text-slate-300">暂无文档</p>
          </div>
        </div>

        <div>
          <button
            class="flex w-full items-center justify-between rounded-lg px-2 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            @click="openSec.public = !openSec.public"
          >
            <span class="flex items-center gap-1.5"><AppIcon name="book" :size="14" /> 公共课标知识库</span>
            <span class="text-slate-400">{{ openSec.public ? '▾' : '▸' }}</span>
          </button>
          <div v-if="openSec.public" class="pl-4">
            <div
              class="cursor-pointer rounded px-2 py-1 text-xs text-primary-600 hover:bg-primary-50"
              @click="selectRef({ type: 'collection', key: 'public', label: '公共课标知识库' })"
            >
              @ 整个分类
            </div>
            <div
              v-for="d in tree.public"
              :key="d.id"
              class="cursor-pointer truncate rounded px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
              @click="selectRef({ type: 'doc', id: d.id, label: '《' + d.title + '》' })"
            >
              {{ d.title }}
            </div>
            <p v-if="!tree.public.length" class="px-2 py-1 text-xs text-slate-300">暂无文档</p>
          </div>
        </div>
      </aside>

      <!-- 右侧对话 -->
      <div class="flex flex-1 flex-col rounded-xl border border-slate-200 bg-white">
        <div ref="boxRef" class="flex-1 space-y-4 overflow-y-auto p-5">
          <div
            v-for="(m, i) in visibleMessages"
            :key="i"
            class="flex"
            :class="m.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div class="max-w-[82%]">
              <div v-if="m.role === 'user' && m.ref" class="mb-1 text-right text-xs text-primary-500">
                引用：{{ m.ref }}
              </div>
              <div
                class="whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed"
                :class="m.role === 'user' ? 'rounded-br-sm bg-primary-600 text-white' : 'rounded-bl-sm bg-slate-100 text-slate-800'"
              >
                {{ m.content }}
              </div>
              <div v-if="m.role === 'assistant' && m.scope" class="mt-1 text-xs text-slate-400">来源：{{ m.scope }}</div>
              <div v-if="m.role === 'assistant' && m.content" class="mt-1 flex gap-3 text-xs text-slate-400">
                <button v-if="m.error" class="font-medium text-primary-600 hover:text-primary-700" @click="send(m.retry)">重试</button>
                <button class="transition-colors hover:text-slate-700" @click="copyMsg(m)">复制</button>
                <button
                  class="transition-colors hover:text-amber-500"
                  :class="m.fav ? 'text-amber-500' : ''"
                  @click="toggleFav(m)"
                >
                  {{ m.fav ? '已收藏' : '收藏' }}
                </button>
                <button class="transition-colors hover:text-slate-700" @click="toDoc(m)">转为文档</button>
              </div>
            </div>
          </div>
          <div v-if="sending" class="flex justify-start">
            <div class="rounded-2xl rounded-bl-sm bg-slate-100 px-4 py-3 text-sm text-slate-400">正在思考…</div>
          </div>
        </div>

        <div class="flex gap-2 border-t border-slate-100 p-3">
          <div class="relative flex-1">
            <input
              v-model="input"
              class="h-11 w-full rounded-lg border border-slate-300 bg-white px-4 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/30"
              placeholder="输入问题，可输入 @ 引用文档，或直接提问…"
              @keyup.enter="send()"
            />
            <div
              v-if="input.includes('@')"
              class="absolute bottom-full left-0 z-10 mb-1 max-h-56 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg"
            >
              <div
                v-for="r in mentionMatches"
                :key="r.label"
                class="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-primary-50"
                @click="pickMention(r)"
              >
                <AppIcon :name="r.type === 'doc' ? 'file' : 'book'" :size="14" /> {{ r.label }}
              </div>
              <p v-if="!mentionMatches.length" class="px-3 py-2 text-xs text-slate-400">无匹配文档</p>
            </div>
          </div>
          <Button size="lg" :disabled="sending" @click="send()"><AppIcon name="send" :size="16" /> 发送</Button>
        </div>
      </div>
    </div>

    <!-- 会话历史面板 -->
    <div v-if="showHistory" class="fixed inset-0 z-40 bg-black/20" @click="showHistory = false"></div>
    <div v-if="showHistory" class="fixed inset-y-0 right-0 z-50 flex w-80 flex-col bg-white shadow-2xl">
      <div class="flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <span class="text-sm font-semibold text-slate-800">会话历史</span>
        <button class="text-slate-400 hover:text-slate-600" @click="showHistory = false"><AppIcon name="x" :size="16" /></button>
      </div>
      <div class="flex-1 overflow-y-auto p-3">
        <p v-if="!sessions.length" class="py-10 text-center text-sm text-slate-400">暂无历史会话</p>
        <div
          v-for="s in sessions"
          :key="s.id"
          class="mb-2 cursor-pointer rounded-lg border border-slate-200 p-3 transition-colors hover:border-primary-300 hover:bg-primary-50/40"
          @click="loadSession(s)"
        >
          <div class="flex items-center justify-between">
            <span class="truncate text-sm font-medium text-slate-800">{{ s.title }}</span>
            <button class="text-slate-300 hover:text-red-500" @click.stop="deleteSession(s.id)">
              <AppIcon name="trash" :size="14" />
            </button>
          </div>
          <div class="mt-1 text-xs text-slate-400">{{ s.updatedAt }} · {{ s.count }} 条消息</div>
        </div>
      </div>
    </div>
  </div>
</template>
