<template>
  <div class="comparador-view fade-in">

    <!-- Encabezado -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Comparador de análisis</h1>
        <p class="page-desc">
          Selecciona dos o más análisis completados para generar un informe global comparativo.
        </p>
      </div>
    </div>

    <!-- Lista de jobs completados -->
    <section class="card jobs-section">
      <div class="section-label">Análisis disponibles</div>

      <div v-if="cargandoJobs" class="estado-loading">
        <span class="pulse-dot" /> Cargando análisis…
      </div>

      <div v-else-if="errorJobs" class="error-banner">
        <span>⚠</span> {{ errorJobs }}
      </div>

      <div v-else-if="jobs.length === 0" class="empty-state">
        No hay análisis completados todavía.
        <router-link to="/" class="link-accent">Crear uno nuevo →</router-link>
      </div>

      <template v-else>
        <div class="jobs-list">
          <label
            v-for="job in jobs"
            :key="job.id"
            class="job-item"
            :class="{ selected: seleccionados.includes(job.id) }"
          >
            <input
              type="checkbox"
              :value="job.id"
              v-model="seleccionados"
            />
            <div class="job-body">
              <div class="job-row">
                <span class="job-dataset">
                  {{ nombreDataset(job) }}
                </span>
                <span class="badge badge-done">completado</span>
              </div>
              <div class="job-meta">
                <span v-if="job.metrica_seleccionada" class="job-metrica">
                  <code>{{ job.metrica_seleccionada }}</code>
                </span>
                <span class="job-fecha">{{ formatFecha(job.creado_en) }}</span>
                <span class="job-id-text">{{ job.id.substring(0, 8) }}…</span>
              </div>
            </div>
          </label>
        </div>

        <!-- Acciones -->
        <div class="comparador-actions">
          <span class="sel-count">
            {{ seleccionados.length }} seleccionado{{ seleccionados.length !== 1 ? 's' : '' }}
          </span>
          <button
            class="btn-primary"
            :disabled="seleccionados.length < 1 || generando"
            @click="generarInforme"
          >
            <span v-if="generando" class="spinner" />
            <span v-else>Generar informe global</span>
          </button>
        </div>
      </template>
    </section>

    <!-- Resultado del informe global -->
    <section v-if="informeHtml || errorInforme" class="card informe-section fade-in">
      <div class="informe-header">
        <div class="section-label">Informe global</div>
        <button
          v-if="informeHtml"
          class="btn-secondary"
          @click="descargarInforme"
        >
          Descargar .md
        </button>
      </div>

      <div v-if="errorInforme" class="error-banner" style="margin-top:0">
        <span>⚠</span> {{ errorInforme }}
      </div>

      <article
        v-if="informeHtml"
        class="prose-fuzhify"
        v-html="informeHtml"
      />
    </section>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import MarkdownIt from 'markdown-it'
import api from '@/api/client'
import type { JobStatus } from '@/api/client'

const jobs          = ref<JobStatus[]>([])
const seleccionados = ref<string[]>([])
const cargandoJobs  = ref(true)
const errorJobs     = ref('')
const generando     = ref(false)
const errorInforme  = ref('')
const informeRaw    = ref('')
const informeHtml   = ref('')

const md = new MarkdownIt({ html: false, linkify: true, typographer: true })

// Carga los jobs completados
onMounted(async () => {
  try {
    const { data } = await api.get<JobStatus[]>('/jobs', {
      params: { estado: 'completado', limit: 20 },
    })
    jobs.value = data
  } catch (e: any) {
    errorJobs.value = e.response?.data?.detail ?? 'Error al cargar los análisis'
  } finally {
    cargandoJobs.value = false
  }
})

// Genera el informe global con los jobs seleccionados
async function generarInforme() {
  generando.value = true
  errorInforme.value = ''
  informeHtml.value = ''
  informeRaw.value = ''

  try {
    const { data } = await api.post<string>('/informe-global',
      { job_ids: seleccionados.value },
      { responseType: 'text' }
    )
    informeRaw.value = data
    informeHtml.value = md.render(data)
  } catch (e: any) {
    errorInforme.value = e.response?.data?.detail ?? 'Error al generar el informe'
  } finally {
    generando.value = false
  }
}

// Descarga el informe como .md
function descargarInforme() {
  const blob = new Blob([informeRaw.value], { type: 'text/markdown' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = 'informe_global.md'
  a.click()
  URL.revokeObjectURL(url)
}

function formatFecha(iso: string) {
  return new Date(iso).toLocaleString('es-ES', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

// El nombre del dataset no está en JobStatus, usamos el id truncado como fallback
function nombreDataset(job: JobStatus): string {
  return `Job ${job.id.substring(0, 8)}…`
}
</script>

<style scoped>
.comparador-view { display: flex; flex-direction: column; gap: 24px; }

.page-header { margin-bottom: 4px; }
.page-title { font-size: 1.6rem; font-weight: 800; margin-bottom: 8px; }
.page-desc  { font-size: 0.9rem; color: var(--c-muted); max-width: 560px; line-height: 1.6; }

.section-label {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--c-accent);
  margin-bottom: 16px;
}

/* Lista de jobs */
.jobs-section { padding: 20px 24px; }

.jobs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.job-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: var(--c-raised);
  border: 1px solid var(--c-border);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.job-item input[type="checkbox"] { margin-top: 3px; accent-color: var(--c-accent); }
.job-item.selected {
  border-color: var(--c-accent);
  background: rgba(249,115,22,0.05);
}

.job-body { flex: 1; }
.job-row  { display: flex; align-items: center; gap: 10px; margin-bottom: 5px; }
.job-dataset {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--c-text);
}

.job-meta { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.job-metrica code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.78rem;
  color: var(--c-accent);
  background: var(--c-dim);
  padding: 1px 6px;
  border-radius: 4px;
}
.job-fecha, .job-id-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  color: var(--c-muted);
}

/* Acciones */
.comparador-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  border-top: 1px solid var(--c-border);
  padding-top: 16px;
}
.sel-count {
  font-size: 0.78rem;
  color: var(--c-muted);
  font-family: 'JetBrains Mono', monospace;
}

/* Informe resultante */
.informe-section { padding: 24px 28px; }
.informe-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.informe-header .section-label { margin-bottom: 0; }

/* Estado vacío */
.empty-state {
  padding: 32px;
  text-align: center;
  color: var(--c-muted);
  font-size: 0.9rem;
}
.link-accent {
  color: var(--c-accent);
  text-decoration: none;
  margin-left: 6px;
}
.link-accent:hover { text-decoration: underline; }

/* Comunes */
.estado-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--c-muted);
  font-size: 0.9rem;
  padding: 24px 0;
}
.pulse-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--c-accent);
  animation: pulse-dot 1.2s ease-in-out infinite;
}
.error-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  margin-top: 8px;
  background: rgba(239,68,68,0.1);
  border: 1px solid rgba(239,68,68,0.3);
  border-radius: 8px;
  color: var(--c-error);
  font-size: 0.85rem;
}
.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
