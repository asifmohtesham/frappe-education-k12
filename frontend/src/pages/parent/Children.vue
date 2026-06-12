<template>
  <div class="p-8">
    <h1 class="mb-4 text-2xl font-semibold">{{ $t('parent.myChildren') }}</h1>
    <div v-if="children.loading" class="text-gray-500">{{ $t('common.loading') }}</div>
    <p v-else-if="!children.data?.length" class="text-gray-600">
      {{ $t('parent.noChildren') }}
    </p>
    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <router-link
        v-for="child in children.data"
        :key="child.name"
        :to="{ name: 'ChildProfile', params: { studentId: child.name } }"
        class="rounded-lg border p-4 hover:shadow"
      >
        <div class="text-lg font-medium">{{ child.student_name }}</div>
        <div v-if="child.enrollment" class="text-sm text-gray-600">
          {{ child.enrollment.program }} · {{ child.enrollment.academic_year }}
        </div>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { children } from '../../data/portal'
children.fetch()
</script>
