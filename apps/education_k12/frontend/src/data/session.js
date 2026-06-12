import { computed, reactive } from 'vue'
import { createResource } from 'frappe-ui'

export function sessionUser() {
  const cookie = document.cookie
    .split('; ')
    .find((c) => c.startsWith('user_id='))
  let user = cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : null
  if (user === 'Guest') user = null
  return user
}

export const session = reactive({
  user: sessionUser(),
  isLoggedIn: computed(() => !!session.user),
  login: createResource({
    url: 'login',
    makeParams({ email, password }) {
      return { usr: email, pwd: password }
    },
    onSuccess() {
      session.user = sessionUser()
      window.location.replace('/portal')
    },
  }),
  logout: createResource({
    url: 'logout',
    onSuccess() {
      session.user = null
      window.location.replace('/portal/login')
    },
  }),
})
