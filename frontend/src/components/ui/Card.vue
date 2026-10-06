<script setup>
defineProps({
  title: { type: String, default: '' },
})
</script>

<template>
  <div class="card">
    <div v-if="title || $slots.header" class="border-b border-slate-100 px-5 py-4">
      <slot name="header">
        <h3 class="text-base font-semibold text-slate-800">{{ title }}</h3>
      </slot>
    </div>
    <div class="p-5">
      <slot />
    </div>
  </div>
</template>
