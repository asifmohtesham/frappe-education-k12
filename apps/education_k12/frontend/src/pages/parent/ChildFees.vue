<template>
  <div class="p-8">
    <router-link
      class="text-sm text-blue-600"
      :to="{ name: 'ChildProfile', params: { studentId: route.params.studentId } }"
    >
      ← {{ $t('parent.backToProfile') }}
    </router-link>
    <h1 class="mb-4 mt-2 text-2xl font-semibold">{{ $t('parent.fees') }}</h1>
    <div v-if="fees.loading" class="text-gray-500">{{ $t('common.loading') }}</div>
    <p v-else-if="!fees.data?.length" class="text-gray-600">
      {{ $t('parent.noFees') }}
    </p>
    <div v-else class="space-y-6">
      <div v-for="bill in fees.data" :key="bill.name" class="rounded-lg border p-4">
        <div class="mb-2 flex items-center justify-between">
          <div>
            <div class="font-medium">{{ bill.name }}</div>
            <div class="text-sm text-gray-600">
              {{ $t('parent.dueDate') }}: {{ bill.due_date }}
            </div>
          </div>
          <div class="text-end">
            <div class="text-lg font-semibold">
              {{ bill.grand_total }} {{ bill.currency }}
            </div>
            <div
              class="text-sm"
              :class="bill.outstanding_amount > 0 ? 'text-orange-600' : 'text-green-600'"
            >
              {{
                bill.outstanding_amount > 0
                  ? $t('parent.outstanding') + ': ' + bill.outstanding_amount
                  : $t('parent.paid')
              }}
            </div>
          </div>
        </div>
        <table class="mb-3 w-full text-sm">
          <tbody>
            <tr v-for="component in bill.components" :key="component.fees_category" class="border-t">
              <td class="py-1">{{ component.fees_category }}</td>
              <td class="py-1 text-end">
                {{ component.total }}
                <span v-if="component.discount" class="text-xs text-gray-500">
                  (-{{ component.discount }}%)
                </span>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="flex gap-2">
          <Button
            v-if="bill.outstanding_amount > 0"
            variant="solid"
            :loading="payingBill === bill.name"
            @click="pay(bill.name)"
          >
            {{ $t('parent.payNow') }}
          </Button>
          <a
            v-if="bill.outstanding_amount < bill.grand_total"
            class="text-sm text-blue-600 underline"
            :href="receiptUrl(bill.name)"
            target="_blank"
          >
            {{ $t('parent.downloadReceipt') }}
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { Button } from 'frappe-ui'
import { childFees, initiatePayment } from '../../data/portal'

const route = useRoute()
const fees = childFees(route.params.studentId)
const payingBill = ref(null)

async function pay(billName) {
  payingBill.value = billName
  try {
    const result = await initiatePayment.submit({ fees_name: billName })
    window.location.href = result.payment_url
  } finally {
    payingBill.value = null
  }
}

function receiptUrl(billName) {
  return `/api/method/education_k12.api.fees.download_receipt?fees_name=${encodeURIComponent(billName)}`
}
</script>
