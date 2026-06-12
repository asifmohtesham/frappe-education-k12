import { createRouter, createWebHistory } from 'vue-router'
import { session } from './data/session'

const routes = [
  { path: '/', name: 'Home', component: () => import('./pages/Home.vue') },
  { path: '/login', name: 'Login', component: () => import('./pages/Login.vue') },
  {
    path: '/teacher/homerooms',
    name: 'TeacherHomerooms',
    component: () => import('./pages/teacher/Homerooms.vue'),
  },
  {
    path: '/teacher/homerooms/:groupId',
    name: 'HomeroomRoster',
    component: () => import('./pages/teacher/HomeroomRoster.vue'),
  },
]

const router = createRouter({
  history: createWebHistory('/portal'),
  routes,
})

router.beforeEach((to) => {
  if (to.name !== 'Login' && !session.isLoggedIn) return { name: 'Login' }
  if (to.name === 'Login' && session.isLoggedIn) return { name: 'Home' }
})

export default router
