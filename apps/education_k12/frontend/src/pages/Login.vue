<template>
  <div class="flex h-screen items-center justify-center">
    <form
      class="w-80 space-y-4"
      @submit.prevent="session.login.submit({ email, password })"
    >
      <h1 class="text-2xl font-semibold">{{ $t('login.title') }}</h1>
      <Input :label="$t('login.email')" type="text" v-model="email" />
      <Input :label="$t('login.password')" type="password" v-model="password" />
      <Button type="submit" variant="solid" class="w-full" :loading="session.login.loading">
        {{ $t('login.submit') }}
      </Button>
      <ErrorMessage :message="session.login.error" />
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Button, Input, ErrorMessage } from 'frappe-ui'
import { session } from '../data/session'

const email = ref('')
const password = ref('')
</script>
