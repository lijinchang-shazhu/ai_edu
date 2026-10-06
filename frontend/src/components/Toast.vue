<script setup>
import { toasts } from './toast'
</script>

<template>
  <div class="pointer-events-none fixed top-4 right-4 z-50 flex flex-col gap-2">
    <TransitionGroup name="toast">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="pointer-events-auto rounded-lg px-4 py-3 text-sm font-medium text-white shadow-lg"
        :class="
          t.type === 'success'
            ? 'bg-emerald-600'
            : t.type === 'error'
              ? 'bg-red-600'
              : 'bg-slate-800'
        "
      >
        {{ t.message }}
      </div>
    </TransitionGroup>
  </div>
</template>
