<template>
  <div class="status-view fade-in">

    <!-- Encabezado con info del job -->
    <div class="page-header">
      <button class="btn-back" @click="router.push('/')">← Inicio</button>
      <div>
        <h1 class="page-title">Estado del análisis</h1>
        <p class="job-id">
          <code>{{ jobId }}</code>
        </p>
      </div>
    </div>

    <!-- Cargando inicial -->
    <div v-if="!job && !error" class="estado-loading">
      <span class="pulse-dot" />
      Consultando estado…
    </div>

    <!-- Error de red -->
    <div v-else-if="error && !job" class="error-banner">
      <span>⚠</span> {{ error }}
      <button class="btn-secondary" style="margin-left:auto" @click="router.push('/')">Volver al inicio</button>
    </div>

    <template v-else-if="job">

      <!-- Tarjeta de estado -->
      <div class="card estado-card">

        <!-- Badge de estado -->
        <div class="estado-top">
          <span class="badge" :class="badgeClass">
            <span v-if="estaEnProceso" class="dot-anim" />
            {{ etiquetaEstado }}
          </span>
          <span class="last-update">Actualizado: {{ horaActualizado }}</span>
        </div>

        <!-- Pipeline visual (solo mientras procesa o completado) -->
        <ProgressPipeline
          v-if="job.estado !== 'esperando_metrica'"
          :estado="job.estado"
          :fase-actual="job.fase_actual"
          class="pipeline-section"
        />

        <!-- Métrica analizada -->
        <div v-if="job.metrica_seleccionada" class="metrica-row">
          <span class="metrica-label">Métrica analizada:</span>
          <code class="metrica-val">{{ job.metrica_seleccionada }}</code>
        </div>

        <!-- Error del pipeline -->
        <div v-if="job.estado === 'error'" class="error-detail">
          <div class="error-title">El análisis terminó con error</div>
          <pre v-if="job.error_mensaje" class="error-msg">{{ job.error_mensaje }}</pre>
          <button class="btn-primary" style="margin-top:16px" @click="router.push('/')">
            Volver al inicio
          </button>
        </div>

        <!-- Acciones cuando está completado -->
        <div v-if="job.estado === 'completado'" class="acciones">
          <div class="acciones-label">Resultados listos</div>
          <div class="acciones-btns">
            <button class="btn-primary" @click="irAInforme">
              Ver informe
            </button>
            <button class="btn-secondary" @click="irAReglas">
              Ver reglas
            </button>
            <a
              :href="`${apiBase}/jobs/${jobId}/descargar/informe`"
              target="_blank"
              class="btn-secondary"
            >
              Descargar .md
            </a>
            <a
              :href="`${apiBase}/jobs/${jobId}/informe.pdf`"
              target="_blank"
              class="btn-secondary"
            >
              Descargar PDF
            </a>
            <a
              :href="`${apiBase}/jobs/${jobId}/descargar/reglas`"
              target="_blank"
              class="btn-secondary"
            >
              Descargar reglas CSV
            </a>
          </div>
        </div>

      </div>

      <!-- Metadatos del job -->
      <div class="card meta-card">
        <div class="section-label">Metadatos</div>
        <dl class="meta-grid">
          <div class="meta-item">
            <dt>ID</dt>
            <dd><code>{{ job.id }}</code></dd>
          </div>
          <div class="meta-item">
            <dt>Estado</dt>
            <dd>{{ job.estado }}</dd>
          </div>
          <div class="meta-item">
            <dt>Fase actual</dt>
            <dd>{{ job.fase_actual ?? '—' }}</dd>
          </div>
          <div class="meta-item">
            <dt>Creado</dt>
            <dd>{{ formatFecha(job.creado_en) }}</dd>
          </div>
        </dl>
      </div>

    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import type { JobStatus } from '@/api/client'
import ProgressPipeline from '@/components/ProgressPipeline.vue'

const route  = useRoute()
const router = useRouter()

const jobId  = computed(() => route.params.id as string)
const job    = ref<JobStatus | null>(null)
const error  = ref('')
const apiBase = import.meta.env.VITE_API_URL as string

// Polling
let intervalo: ReturnType<typeof setInterval> | null = null
const INTERVALO_MS = 2000

async function fetchJob() {
  try {
    const { data } = await api.get<JobStatus>(`/jobs/${jobId.value}`)
    job.value = data
    // Detener polling si ya terminó
    if (data.estado === 'completado' || data.estado === 'error') {
      pararPolling()
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail ?? 'No se pudo consultar el job'
    pararPolling()
  }
}

function pararPolling() {
  if (intervalo !== null) {
    clearInterval(intervalo)
    intervalo = null
  }
}

onMounted(() => {
  fetchJob()
  // Solo hacer polling si no está en estado terminal
  intervalo = setInterval(() => {
    if (job.value?.estado !== 'completado' && job.value?.estado !== 'error') {
      fetchJob()
    } else {
      pararPolling()
    }
  }, INTERVALO_MS)
})

onUnmounted(() => pararPolling())

// ── Computadas de presentación ──
const estaEnProceso = computed(() =>
  job.value ? !['completado', 'error', 'esperando_metrica'].includes(job.value.estado) : false
)

const etiquetaEstado = computed(() => {
  const map: Record<string, string> = {
    esperando_metrica: 'Esperando métrica',
    pendiente:         'En cola',
    fuzzificacion:     'Fuzzificando',
    mineria:           'Minería de reglas',
    nlg:               'Generando informe',
    completado:        'Completado',
    error:             'Error',
  }
  return map[job.value?.estado ?? ''] ?? job.value?.estado ?? '—'
})

const badgeClass = computed(() => {
  switch (job.value?.estado) {
    case 'completado':        return 'badge badge-done'
    case 'error':             return 'badge badge-error'
    case 'pendiente':
    case 'esperando_metrica': return 'badge badge-pending'
    default:                  return 'badge badge-running'
  }
})

const horaActualizado = computed(() => {
  if (!job.value) return ''
  return new Date(job.value.actualizado_en).toLocaleTimeString('es-ES')
})

function formatFecha(iso: string) {
  return new Date(iso).toLocaleString('es-ES')
}

function irAInforme() {
  router.push({ name: 'job-informe', params: { id: jobId.value } })
}
function irAReglas() {
  router.push({ name: 'job-reglas', params: { id: jobId.value } })
}
</script>

<style scoped>
.status-view { display: flex; flex-direction: column; gap: 20px; }

.page-header { display: flex; align-items: flex-start; gap: 16px; }
.btn-back {
  flex-shrink: 0;
  background: transparent;
  border: 1px solid var(--c-border);
  color: var(--c-muted);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
  margin-top: 6px;
  transition: border-color 0.15s, color 0.15s;
}
.btn-back:hover { border-color: var(--c-accent); color: var(--c-accent); }

.page-title { font-size: 1.6rem; font-weight: 800; margin-bottom: 4px; }
.job-id code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--c-muted);
}

/* Cargando */
.estado-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--c-muted);
  font-size: 0.9rem;
  padding: 40px 0;
}

/* Tarjeta estado */
.estado-card { padding: 24px; display: flex; flex-direction: column; gap: 20px; }

.estado-top { display: flex; align-items: center; justify-content: space-between; }

.dot-anim {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse-dot 1.2s ease-in-out infinite;
}

.last-update { font-size: 0.72rem; color: var(--c-muted); font-family: 'JetBrains Mono', monospace; }

.pipeline-section { padding: 8px 0; }

/* Métrica */
.metrica-row { display: flex; align-items: center; gap: 10px; }
.metrica-label { font-size: 0.78rem; color: var(--c-muted); text-transform: uppercase; letter-spacing: 0.06em; }
.metrica-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  color: var(--c-accent);
  background: var(--c-dim);
  padding: 2px 10px;
  border-radius: 6px;
}

/* Error */
.error-detail { padding: 16px; background: rgba(239,68,68,0.07); border: 1px solid rgba(239,68,68,0.25); border-radius: 10px; }
.error-title { font-weight: 700; color: var(--c-error); margin-bottom: 8px; }
.error-msg {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.78rem;
  color: #FCA5A5;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}

/* Acciones */
.acciones { border-top: 1px solid var(--c-border); padding-top: 20px; }
.acciones-label {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--c-success);
  margin-bottom: 14px;
}
.acciones-btns { display: flex; gap: 10px; flex-wrap: wrap; }
.acciones-btns a { text-decoration: none; }

/* Error banner */
.error-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background: rgba(239,68,68,0.1);
  border: 1px solid rgba(239,68,68,0.3);
  border-radius: 8px;
  color: var(--c-error);
  font-size: 0.85rem;
}

/* Metadatos */
.meta-card { padding: 20px; }
.section-label {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--c-accent);
  margin-bottom: 14px;
}
.meta-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.meta-item dt {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--c-muted);
  margin-bottom: 2px;
}
.meta-item dd {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.82rem;
  color: var(--c-text);
  word-break: break-all;
}
.meta-item dd code {
  color: var(--c-muted);
  font-size: 0.75rem;
}

/* Pulse dot */
.pulse-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--c-accent);
  animation: pulse-dot 1.2s ease-in-out infinite;
}
</style>
