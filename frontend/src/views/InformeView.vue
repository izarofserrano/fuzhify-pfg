<template>
  <div class="informe-view fade-in">

    <!-- Cabecera -->
    <div class="page-header">
      <button class="btn-back" @click="router.back()">← Volver</button>
      <div>
        <h1 class="page-title">Informe del análisis</h1>
        <p class="job-id"><code>{{ jobId }}</code></p>
      </div>
      <div class="header-actions">
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
      </div>
    </div>

    <!-- Cargando -->
    <div v-if="cargando" class="estado-loading">
      <span class="pulse-dot" /> Cargando informe…
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-banner">
      <span>⚠</span> {{ error }}
    </div>

    <!-- Contenido markdown renderizado -->
    <article
      v-else
      class="card informe-card prose-fuzhify"
      v-html="htmlRendered"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'
import api from '@/api/client'

const route  = useRoute()
const router = useRouter()

const jobId   = computed(() => route.params.id)
const apiBase = import.meta.env.VITE_API_URL

const cargando    = ref(true)
const error       = ref('')
const markdownRaw = ref('')

const md = new MarkdownIt({ html: false, linkify: true, typographer: true })
const htmlRendered = computed(() => md.render(markdownRaw.value))

onMounted(async () => {
  try {
    const { data } = await api.get(`/jobs/${jobId.value}/informe`, {
      responseType: 'text',
    })
    markdownRaw.value = data
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'No se pudo cargar el informe'
  } finally {
    cargando.value = false
  }
})
</script>

<style scoped>
.informe-view { display: flex; flex-direction: column; gap: 20px; }

.page-header { display: flex; align-items: flex-start; gap: 16px; }
.header-actions { margin-left: auto; display: flex; gap: 10px; align-items: center; }

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
  text-decoration: none;
}
.btn-back:hover { border-color: var(--c-accent); color: var(--c-accent); }

.page-title { font-size: 1.6rem; font-weight: 800; margin-bottom: 4px; }
.job-id code { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--c-muted); }

.estado-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--c-muted);
  font-size: 0.9rem;
  padding: 40px 0;
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
  background: rgba(239,68,68,0.1);
  border: 1px solid rgba(239,68,68,0.3);
  border-radius: 8px;
  color: var(--c-error);
  font-size: 0.85rem;
}

.informe-card { padding: 36px 40px; max-width: 820px; }

.header-actions a { text-decoration: none; }
</style>
