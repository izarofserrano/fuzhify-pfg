import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { JobStatus } from '@/api/client'

// Store Pinia para el estado global de jobs
export const useJobsStore = defineStore('jobs', () => {
  // Job que acaba de lanzarse (para pasar datos entre vistas sin router params extra)
  const jobActual = ref<JobStatus | null>(null)

  function setJobActual(job: JobStatus) {
    jobActual.value = job
  }

  function limpiar() {
    jobActual.value = null
  }

  return { jobActual, setJobActual, limpiar }
})
