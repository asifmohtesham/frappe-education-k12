<template>
  <div class="p-8">
    <router-link class="text-sm text-blue-600" :to="{ name: 'Children' }">
      ← {{ $t('parent.myChildren') }}
    </router-link>
    <div v-if="profile.loading" class="mt-4 text-gray-500">{{ $t('common.loading') }}</div>
    <template v-else-if="profile.data">
      <h1 class="mb-4 mt-2 text-2xl font-semibold">{{ profile.data.student_name }}</h1>
      <dl class="grid max-w-xl grid-cols-2 gap-x-6 gap-y-3">
        <template v-for="field in profileFields" :key="field.key">
          <dt class="text-sm text-gray-600">{{ $t(field.label) }}</dt>
          <dd class="text-sm">{{ field.value() || '—' }}</dd>
        </template>
      </dl>
    </template>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { childProfile } from '../../data/portal'

const route = useRoute()
const profile = childProfile(route.params.studentId)

const profileFields = [
  { key: 'grade', label: 'parent.grade', value: () => profile.data?.enrollment?.program },
  { key: 'year', label: 'parent.academicYear', value: () => profile.data?.enrollment?.academic_year },
  { key: 'homeroom', label: 'parent.homeroom', value: () => profile.data?.homeroom },
  { key: 'dob', label: 'parent.dateOfBirth', value: () => profile.data?.date_of_birth },
  { key: 'nationality', label: 'parent.nationality', value: () => profile.data?.nationality },
  { key: 'blood', label: 'parent.bloodGroup', value: () => profile.data?.blood_group },
  { key: 'medical', label: 'parent.medical', value: () => profile.data?.medical_conditions },
  { key: 'emName', label: 'parent.emergencyContact', value: () => profile.data?.emergency_contact_name },
  { key: 'emPhone', label: 'parent.emergencyPhone', value: () => profile.data?.emergency_contact_phone },
  { key: 'busRoute', label: 'parent.busRoute', value: () => profile.data?.transport?.route },
  { key: 'busStop', label: 'parent.busStop', value: () => profile.data?.transport?.stop },
  { key: 'busPickup', label: 'parent.busPickup', value: () => profile.data?.transport?.pickup_time },
]
</script>
