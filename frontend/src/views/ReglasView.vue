<template>
  <div class="reglas-view fade-in">

    <!-- Cabecera -->
    <div class="page-header">
      <button class="btn-back" @click="router.back()">← Volver</button>
      <div>
        <h1 class="page-title">Reglas de asociación</h1>
        <p class="job-id"><code>{{ jobId }}</code></p>
      </div>
    </div>

    <!-- Controles: filtro + descarga -->
    <div class="controls card">
      <div class="controls-left">
        <!-- Filtro por consecuente -->
        <div class="control-group">
          <label class="field-label">Filtrar por consecuente</label>
          <select v-model="filtroConsecuente" class="field" style="width:220px" @change="onFiltroChange">
            <option value="">Todos</option>
            <option v-for="c in consecuentesUnicos" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>

        <!-- Total -->
        <div class="total-badge">
          <span class="total-num">{{ total }}</span>
          <span class="total-label">reglas</span>
        </div>
      </div>

      <div class="controls-right">
        <a
          :href="`${apiBase}/jobs/${jobId}/descargar/reglas`"
          target="_blank"
          class="btn-secondary"
        >
          Descargar CSV
        </a>
      </div>
    </div>

    <!-- Cargando -->
    <div v-if="cargando" class="estado-loading">
      <span class="pulse-dot" /> Cargando reglas…
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-banner">
      <span>⚠</span> {{ error }}
    </div>

    <!-- Tabla -->
    <template v-else>
      <div class="table-wrap card">
        <table class="reglas-table">
          <thead>
            <tr>
              <th>Antecedente</th>
              <th>Consecuente</th>
              <th class="num-col">Soporte</th>
              <th class="num-col">Confianza</th>
              <th class="num-col">Lift</th>
              <th class="num-col">N vars</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in items" :key="i">
              <td class="mono">{{ r.antecedente }}</td>
              <td class="mono consec">{{ r.consecuente }}</td>
              <td class="num-col mono">{{ (r.soporte * 100).toFixed(1) }}%</td>
              <td class="num-col mono">{{ (r.confianza * 100).toFixed(1) }}%</td>
              <td class="num-col">
                <span class="lift-chip" :class="liftClass(r.lift)">
                  {{ r.lift.toFixed(2) }}
                </span>
              </td>
              <td class="num-col mono muted">{{ r.n_vars }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Paginación -->
      <div class="pagination">
        <button
          class="btn-secondary"
          :disabled="offset === 0"
          @click="irPagina(offset - LIMIT)"
        >
          ← Anterior
        </button>

        <span class="pag-info">
          {{ offset + 1 }}–{{ Math.min(offset + LIMIT, total) }}
          de {{ total }}
        </span>

        <button
          class="btn-secondary"
          :disabled="offset + LIMIT >= total"
          @click="irPagina(offset + LIMIT)"
        >
          Siguiente →
        </button>
      </div>
    </template>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import type { ReglaItem, ReglasResponse } from '@/api/client'

const route  = useRoute()
const router = useRouter()

const jobId   = computed(() => route.params.id as string)
const apiBase = import.meta.env.VITE_API_URL as string

const LIMIT = 50

const cargando = ref(true)
const error    = ref('')
const items    = ref<ReglaItem[]>([])
const total    = ref(0)
const offset   = ref(0)
const filtroConsecuente = ref('')

// Lista de consecuentes únicos para el filtro (se rellena con la primera carga)
const consecuentesUnicos = ref<string[]>([])

async function cargarReglas() {
  cargando.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = {
      limit:  LIMIT,
      offset: offset.value,
    }
    if (filtroConsecuente.value) params.consecuente = filtroConsecuente.value

    const { data } = await api.get<ReglasResponse>(`/jobs/${jobId.value}/reglas`, { params })
    items.value = data.items
    total.value = data.total

    // Poblar la lista de consecuentes únicos la primera vez (sin filtro)
    if (!filtroConsecuente.value && consecuentesUnicos.value.length === 0) {
      const unicos = [...new Set(data.items.map(r => r.consecuente))].sort()
      consecuentesUnicos.value = unicos
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail ?? 'Error al cargar las reglas'
  } finally {
    cargando.value = false
  }
}

function onFiltroChange() {
  offset.value = 0
  cargarReglas()
}

function irPagina(nuevoOffset: number) {
  offset.value = Math.max(0, nuevoOffset)
  cargarReglas()
}

// Color del lift según la escala adverbial de src03
function liftClass(lift: number): string {
  if (lift >= 3.0) return 'lift-muy-alto'
  if (lift >= 2.0) return 'lift-alto'
  if (lift >= 1.5) return 'lift-medio'
  return 'lift-bajo'
}

onMounted(() => cargarReglas())
</script>

<style scoped>
.reglas-view { display: flex; flex-direction: column; gap: 20px; }

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
.job-id code { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--c-muted); }

/* Controles */
.controls {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  flex-wrap: wrap;
}
.controls-left  { display: flex; align-items: flex-end; gap: 20px; }
.controls-right a { text-decoration: none; }

.control-group { display: flex; flex-direction: column; }

.total-badge { display: flex; align-items: baseline; gap: 4px; }
.total-num { font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 600; color: var(--c-accent); }
.total-label { font-size: 0.72rem; color: var(--c-muted); text-transform: uppercase; letter-spacing: 0.06em; }

/* Tabla */
.table-wrap { overflow-x: auto; }

.reglas-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}
.reglas-table thead tr {
  background: var(--c-raised);
  border-bottom: 1px solid var(--c-border);
}
.reglas-table th {
  padding: 10px 12px;
  text-align: left;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--c-muted);
  white-space: nowrap;
}
.reglas-table tbody tr {
  border-bottom: 1px solid rgba(30,39,54,0.5);
  transition: background 0.1s;
}
.reglas-table tbody tr:hover { background: rgba(249,115,22,0.04); }
.reglas-table td { padding: 9px 12px; color: var(--c-text); }

.mono     { font-family: 'JetBrains Mono', monospace; }
.muted    { color: var(--c-muted) !important; }
.num-col  { text-align: right; }
.consec   { color: var(--c-accent) !important; }

/* Chips de lift coloreados según escala src03 */
.lift-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  font-weight: 600;
}
.lift-muy-alto { background: rgba(239,68,68,0.15);  color: #EF4444; }  /* ≥ 3.0 rojo */
.lift-alto     { background: rgba(249,115,22,0.15); color: #F97316; }  /* 2-3 naranja */
.lift-medio    { background: rgba(234,179,8,0.15);  color: #EAB308; }  /* 1.5-2 amarillo */
.lift-bajo     { background: rgba(100,116,139,0.12); color: #64748B; } /* < 1.5 gris */

/* Paginación */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 8px 0;
}
.pag-info {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  color: var(--c-muted);
}

/* Resto de estados */
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
</style>
