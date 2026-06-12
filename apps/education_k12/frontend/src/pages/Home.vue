<template>
  <div class="space-y-4 p-8">
    <h1 class="text-2xl font-semibold">
      {{ $t('home.welcome') }}, {{ session.user }}
    </h1>
    <div class="flex gap-2">
      <Button @click="setLocale('en')">English</Button>
      <Button @click="setLocale('ar')">العربية</Button>
    </div>
    <Button variant="outline" @click="session.logout.submit()">
      {{ $t('home.logout') }}
    </Button>
  </div>
</template>

<script setup>
import { Button } from 'frappe-ui'
import { session } from '../data/session'
import { setLocale } from '../i18n'
</script>
