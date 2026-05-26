import { createRouter, createWebHistory } from 'vue-router'
import HomeView       from '@/views/HomeView.vue'
import JobStatusView  from '@/views/JobStatusView.vue'
import InformeView    from '@/views/InformeView.vue'
import ReglasView     from '@/views/ReglasView.vue'
import ComparadorView from '@/views/ComparadorView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/',                    component: HomeView,       name: 'home' },
    { path: '/jobs/:id',            component: JobStatusView,  name: 'job-status' },
    { path: '/jobs/:id/informe',    component: InformeView,    name: 'job-informe' },
    { path: '/jobs/:id/reglas',     component: ReglasView,     name: 'job-reglas' },
    { path: '/comparador',          component: ComparadorView, name: 'comparador' },
  ],
})

export default router
