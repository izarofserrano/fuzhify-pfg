import axios from 'axios'

// Instancia axios con baseURL desde variable de entorno
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL as string,
})

export default api

// ── Tipos espejo de los schemas Pydantic del backend ──

export interface MetricaCandidata {
  nombre: string
  sugerida: boolean
  razon: string
}

export interface DetectMetricResponse {
  job_id: string
  nombre_dataset: string
  var_tiempo: string
  granularidad_s: number
  candidatas: MetricaCandidata[]
}

export interface ParametrosPipeline {
  min_soporte: number
  min_confianza: number
  lift_minimo: 1.0 | 1.5 | 2.0 | 3.0
  max_prof: number
  k_beam: number
  top_por_consecuente: number
  pais: string
  subdiv: string | null
  min_reglas_grupo: number
}

export interface JobStatus {
  id: string
  estado: string
  fase_actual: string | null
  metrica_seleccionada: string | null
  error_mensaje: string | null
  creado_en: string
  actualizado_en: string
}

export interface ReglaItem {
  antecedente: string
  consecuente: string
  soporte: number
  confianza: number
  lift: number
  n_vars: number
}

export interface ReglasResponse {
  total: number
  items: ReglaItem[]
}
