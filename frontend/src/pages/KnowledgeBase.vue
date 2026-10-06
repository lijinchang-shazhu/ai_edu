<script setup>
import { onMounted, ref } from 'vue'
import api from '../api'
import AppIcon from '../components/AppIcon.vue'
import { teachers, currentTeacher, setTeacher } from '../components/teacher'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import Card from '../components/ui/Card.vue'
import Input from '../components/ui/Input.vue'
import { toast, toastError } from '../components/toast'

const collection = ref('private')
const docs = ref([])
const uploading = ref(false)
const searchQ = ref('')
const searchResults = ref([])

const tabs = [
  { key: 'private', label: '教师私有记忆库' },
  { key: 'public', label: '公共课标知识库' },
  { key: 'auto', label: '自动分类' },
]

async function load() {
  if (collection.value === 'auto') {
    docs.value = []
    return
  }
  try {
    const res = await api.kbList(collection.value, currentTeacher.value)
    docs.value = res.data.documents
  } catch (e) {
    docs.value = []
  }
}

function onTeacherChange(id) {
  setTeacher(id)
  load()
}

async function onFileChange(e) {
  const files = Array.from(e.target.files || [])
  if (!files.length) return
  uploading.value = true
  try {
    let pub = 0
    let priv = 0
    for (const file of files) {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('collection', collection.value)
      fd.append('title', file.name.replace(/\.[^.]+$/, ''))
      fd.append('teacher', currentTeacher.value)
      const res = await api.kbUpload(fd)
      if (res.data.collection === 'public') pub++
      else priv++
    }
    if (collection.value === 'auto') {
      toast(`已上传 ${files.length} 篇并自动分类：公共 ${pub} 篇、私有 ${priv} 篇`)
    } else {
      toast(`已上传 ${files.length} 篇文档`)
    }
    await load()
  } catch (err) {
    toastError('上传失败：' + (err.response?.data?.detail || err.message))
  } finally {
    uploading.value = false
    e.target.value = ''
  }
}

async function remove(id) {
  if (!confirm('确认删除该文档？')) return
  try {
    await api.kbDelete(id)
    toast('已删除')
    await load()
  } catch (err) {
    toastError('删除失败：' + (err.response?.data?.detail || err.message))
  }
}

async function search() {
  if (!searchQ.value.trim()) return
  try {
    const res = await api.kbSearch(searchQ.value.trim(), collection.value, 5, currentTeacher.value)
    searchResults.value = res.data.results
  } catch (err) {
    toastError('检索失败：' + (err.response?.data?.detail || err.message))
  }
}

function switchTab(key) {
  collection.value = key
  searchResults.value = []
  searchQ.value = ''
  load()
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-end justify-between">
      <div>
        <h1 class="page-title">知识库管理</h1>
        <p class="muted mt-1">
          私有记忆库：上传个人教案、反思、试卷；公共知识库：导入名师经验、优秀课例、课标教材
        </p>
      </div>
      <div class="w-48">
        <label class="mb-1 block text-xs text-slate-400">当前教师（私有库隔离）</label>
        <select
          :value="currentTeacher"
          class="h-9 w-full rounded-lg border border-slate-300 bg-white px-2 text-sm text-slate-700 focus:border-primary-500 focus:outline-none"
          @change="onTeacherChange($event.target.value)"
        >
          <option v-for="t in teachers" :key="t.id" :value="t.id">{{ t.label }}</option>
        </select>
      </div>
    </div>

    <div class="flex gap-2">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        :class="collection === t.key ? 'bg-primary-600 text-white shadow-sm' : 'bg-white text-slate-600 hover:bg-slate-100'"
        @click="switchTab(t.key)"
      >
        {{ t.label }}
      </button>
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
      <Card title="上传文档">
        <label
          class="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 py-10 text-center transition-colors hover:border-primary-400 hover:bg-primary-50/40"
        >
          <span class="text-primary-500"><AppIcon name="upload" :size="28" /></span>
          <span class="text-sm text-slate-600">点击选择 PDF / Word 文档（可多选）</span>
          <span class="text-xs text-slate-400">{{ uploading ? '上传中…' : '支持多选文件 · .pdf / .docx / .txt / .md' }}</span>
          <input type="file" class="hidden" accept=".pdf,.docx,.doc,.txt,.md" multiple @change="onFileChange" />
        </label>
      </Card>

      <Card title="智能检索">
        <div class="flex gap-2">
          <Input v-model="searchQ" placeholder="输入关键词，检索历史教学记忆…" />
          <Button class="min-w-[88px] shrink-0" @click="search"><AppIcon name="search" :size="16" /> 检索</Button>
        </div>
        <div v-if="searchResults.length" class="mt-4 space-y-2">
          <div v-for="(r, i) in searchResults" :key="i" class="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
            <Badge variant="secondary">相关度 {{ r.score }}</Badge>
            <p class="mt-1 line-clamp-3 text-slate-600">{{ r.text }}</p>
          </div>
        </div>
        <p v-else class="mt-4 text-xs text-slate-400">检索结果将在此展示</p>
      </Card>
    </div>

    <Card v-if="collection !== 'auto'" :title="`${tabs.find((t) => t.key === collection).label} · 文档列表`">
      <div v-if="docs.length" class="divide-y divide-slate-100">
        <div v-for="d in docs" :key="d.id" class="flex items-center justify-between py-3">
          <div class="flex items-center gap-3">
            <div
              class="flex h-11 w-9 shrink-0 items-center justify-center rounded-md text-white shadow-sm"
              :class="d.collection === 'public' ? 'bg-gradient-to-br from-primary-500 to-violet-600' : 'bg-gradient-to-br from-emerald-500 to-teal-600'"
            >
              <AppIcon name="file" :size="18" />
            </div>
            <div>
              <div class="text-sm font-medium text-slate-800">{{ d.title }}</div>
              <div class="text-xs text-slate-400">
                {{ d.collection === 'public' ? '公共知识库' : '私有记忆库' }} · {{ d.chunk_count }} 个分块 · {{ d.created_at }}
              </div>
            </div>
          </div>
          <Button variant="ghost" size="sm" @click="remove(d.id)"><AppIcon name="trash" :size="16" /></Button>
        </div>
      </div>
      <p v-else class="py-8 text-center text-sm text-slate-400">暂无文档，请先上传</p>
    </Card>
    <Card v-else title="自动分类">
      <p class="py-8 text-center text-sm text-slate-500">
        上传文档后，系统将根据内容自动判断，归入「公共课标知识库」或「教师私有记忆库」
      </p>
    </Card>
  </div>
</template>
