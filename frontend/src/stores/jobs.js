import { defineStore } from 'pinia'
import { ref } from 'vue'

// Store Pinia para el estado global de jobs
export const useJobsStore = defineStore('jobs', () => {
  // Job que acaba de lanzarse (para pasar datos entre vistas sin router params extra)
  const jobActual = ref(null)

  function setJobActual(job) {
    jobActual.value = job
  }

  function limpiar() {
    jobActual.value = null
  }

  return { jobActual, setJobActual, limpiar }
})
