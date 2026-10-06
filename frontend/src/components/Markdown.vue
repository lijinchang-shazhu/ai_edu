<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  content: { type: String, default: '' },
})

const html = computed(() => {
  try {
    return marked.parse(props.content || '')
  } catch (e) {
    return '<p>渲染失败</p>'
  }
})
</script>

<template>
  <div class="md-body" v-html="html" />
</template>
