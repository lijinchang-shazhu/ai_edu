<script setup>
defineProps({
  variant: { type: String, default: 'default' },
})

const variants = {
  default: 'bg-primary-50 text-primary-700',
  success: 'bg-emerald-50 text-emerald-700',
  warning: 'bg-amber-50 text-amber-700',
  danger: 'bg-red-50 text-red-600',
  secondary: 'bg-slate-100 text-slate-600',
}
</script>

<template>
  <span
    class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
    :class="variants[variant]"
  >
    <slot />
  </span>
</template>
