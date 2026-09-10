import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
  },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    children: [
      { path: '', name: 'Home', component: () => import('../views/Home.vue') },
      { path: 'hot', name: 'Hot', component: () => import('../views/Hot.vue') },
      { path: 'upload', name: 'Upload', component: () => import('../views/Upload.vue'), meta: { requiresAuth: true } },
      { path: 'mine', name: 'Mine', component: () => import('../views/Mine.vue'), meta: { requiresAuth: true } },
      { path: 'profile', name: 'Profile', component: () => import('../views/Profile.vue'), meta: { requiresAuth: true } },
      { path: 'tutorial', name: 'Tutorial', component: () => import('../views/Tutorial.vue') },
      { path: 'work/:id', name: 'WorkDetail', component: () => import('../views/WorkDetail.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  if (to.meta.requiresAuth && !userStore.isLogin()) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

export default router
