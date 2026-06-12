<template>
  <div class="p-8">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-semibold">
        {{ $t('home.welcome') }}, {{ portalContext.data?.full_name || session.user }}
      </h1>
      <div class="flex gap-2">
        <Button @click="setLocale('en')">English</Button>
        <Button @click="setLocale('ar')">العربية</Button>
        <Button variant="outline" @click="session.logout.submit()">
          {{ $t('home.logout') }}
        </Button>
      </div>
    </div>
    <p v-if="noAccess" class="text-gray-600">{{ $t('home.noAccess') }}</p>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button } from 'frappe-ui'
import { session } from '../data/session'
import { portalContext } from '../data/portal'
import { homeRouteFor } from '../data/homeRoute'
import { setLocale } from '../i18n'

const router = useRouter()
portalContext.fetch()

const noAccess = computed(
  () => portalContext.data && homeRouteFor(portalContext.data) === 'NoAccess'
)

watch(
  () => portalContext.data,
  (context) => {
    if (!context) return
    const target = homeRouteFor(context)
    if (target !== 'NoAccess') router.replace({ name: target })
  },
  { immediate: true }
)
</script>
