<template>
  <div class="p-8">
    <h1 class="mb-4 text-2xl font-semibold">{{ $t('teacher.myHomerooms') }}</h1>
    <div v-if="homerooms.loading" class="text-gray-500">{{ $t('common.loading') }}</div>
    <p v-else-if="!homerooms.data?.length" class="text-gray-600">
      {{ $t('teacher.noHomerooms') }}
    </p>
    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <router-link
        v-for="group in homerooms.data"
        :key="group.name"
        :to="{ name: 'HomeroomRoster', params: { groupId: group.name } }"
        class="rounded-lg border p-4 hover:shadow"
      >
        <div class="text-lg font-medium">{{ group.student_group_name }}</div>
        <div class="text-sm text-gray-600">
          {{ group.program }} · {{ group.academic_year }}
        </div>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { homerooms } from '../../data/portal'
homerooms.fetch()
</script>
