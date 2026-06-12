<template>
  <div class="p-8">
    <router-link class="text-sm text-blue-600" :to="{ name: 'TeacherHomerooms' }">
      ← {{ $t('teacher.myHomerooms') }}
    </router-link>
    <div v-if="roster.loading" class="mt-4 text-gray-500">{{ $t('common.loading') }}</div>
    <template v-else-if="roster.data">
      <h1 class="mb-4 mt-2 text-2xl font-semibold">
        {{ roster.data.group.student_group_name }}
      </h1>
      <table class="w-full border-collapse text-start">
        <thead>
          <tr class="border-b text-sm text-gray-600">
            <th class="py-2 text-start">{{ $t('teacher.rollNo') }}</th>
            <th class="py-2 text-start">{{ $t('teacher.studentName') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in roster.data.students" :key="row.student" class="border-b">
            <td class="py-2">{{ row.group_roll_number }}</td>
            <td class="py-2">{{ row.student_name }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { homeroomRoster } from '../../data/portal'

const route = useRoute()
const roster = homeroomRoster(route.params.groupId)
</script>
