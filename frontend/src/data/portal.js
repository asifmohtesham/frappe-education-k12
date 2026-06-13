import { createResource } from 'frappe-ui'

export const portalContext = createResource({
  url: 'education_k12.api.portal.get_portal_context',
  cache: 'portal-context',
})

export const homerooms = createResource({
  url: 'education_k12.api.portal.get_homerooms',
  cache: 'homerooms',
})

export function homeroomRoster(groupName) {
  return createResource({
    url: 'education_k12.api.portal.get_homeroom_roster',
    params: { student_group: groupName },
    auto: true,
  })
}

export const children = createResource({
  url: 'education_k12.api.portal.get_children',
  cache: 'children',
})

export function childProfile(studentId) {
  return createResource({
    url: 'education_k12.api.portal.get_child_profile',
    params: { student: studentId },
    auto: true,
  })
}

export function childFees(studentId) {
  return createResource({
    url: 'education_k12.api.fees.get_child_fees',
    params: { student: studentId },
    auto: true,
  })
}

export const initiatePayment = createResource({
  url: 'education_k12.api.fees.initiate_fee_payment',
})
