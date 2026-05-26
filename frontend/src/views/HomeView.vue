<template>
  <div class="home fade-in">

    <!-- Encabezado -->
    <div class="page-header">
      <h1 class="page-title">Nuevo análisis</h1>
      <p class="page-desc">
        Sube una serie temporal en CSV y el sistema detectará patrones difusos mediante
        minería de reglas de asociación.
      </p>
    </div>

    <div class="layout">

      <!-- ── Zona de carga de archivo ── -->
      <section class="card upload-card">
        <div class="section-label">Archivo CSV</div>

        <div
          class="dropzone"
          :class="{ 'dropzone--over': dragging, 'dropzone--loaded': archivoSeleccionado }"
          @dragenter.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @dragover.prevent
          @drop.prevent="onDrop"
          @click="inputRef?.click()"
        >
          <input
            ref="inputRef"
            type="file"
            accept=".csv"
            class="sr-only"
            @change="onFileChange"
          />

          <!-- Sin archivo -->
          <template v-if="!archivoSeleccionado">
            <div class="drop-icon">↑</div>
            <p class="drop-msg">
              Arrastra tu CSV aquí<br/>
              <span class="drop-sub">o haz clic para seleccionar</span>
            </p>
          </template>

          <!-- Archivo cargado -->
          <template v-else>
            <div class="drop-icon drop-icon--ok">✓</div>
            <p class="drop-msg">
              <strong>{{ archivoSeleccionado.name }}</strong><br/>
              <span class="drop-sub">{{ formatBytes(archivoSeleccionado.size) }}</span>
            </p>
            <button class="btn-clear" @click.stop="limpiarArchivo">✕</button>
          </template>
        </div>
      </section>

      <!-- ── Parámetros del pipeline ── -->
      <section class="card params-card">
        <div class="section-label">Parámetros del análisis</div>

        <div class="params-grid">

          <!-- MIN_SOPORTE -->
          <div class="param-group">
            <label class="field-label">
              MIN_SOPORTE
              <span class="tip" data-tip="Proporción mínima de registros que deben cumplir la regla. Valores bajos → más reglas raras.">ⓘ</span>
            </label>
            <input
              v-model.number="params.min_soporte"
              type="number" step="0.001" min="0" max="1"
              class="field"
            />
          </div>

          <!-- MIN_CONFIANZA -->
          <div class="param-group">
            <label class="field-label">
              MIN_CONFIANZA
              <span class="tip" data-tip="P(consecuente | antecedente) mínimo. Valores altos → reglas más fiables.">ⓘ</span>
            </label>
            <input
              v-model.number="params.min_confianza"
              type="number" step="0.01" min="0" max="1"
              class="field"
            />
          </div>

          <!-- LIFT_MINIMO — ocupa columna completa -->
          <div class="param-group param-group--full">
            <label class="field-label">
              LIFT_MÍNIMO
              <span class="tip" data-tip="Umbral de sorpresa de la regla. Lift=1 significa independencia. Cuanto mayor, más sorprendente.">ⓘ</span>
            </label>
            <select v-model.number="params.lift_minimo" class="field">
              <option :value="1.0">Incluir todas &mdash; lift ≥ 1.0</option>
              <option :value="1.5">Algo sorprendentes &mdash; lift ≥ 1.5</option>
              <option :value="2.0">Sorprendentes &mdash; lift ≥ 2.0</option>
              <option :value="3.0">Muy sorprendentes &mdash; lift ≥ 3.0</option>
            </select>
          </div>

          <!-- MAX_PROF -->
          <div class="param-group">
            <label class="field-label">
              MAX_PROF
              <span class="tip" data-tip="Profundidad máxima del antecedente (número de variables).">ⓘ</span>
            </label>
            <input
              v-model.number="params.max_prof"
              type="number" min="1" max="10"
              class="field"
            />
          </div>

          <!-- K_BEAM -->
          <div class="param-group">
            <label class="field-label">
              K_BEAM
              <span class="tip" data-tip="Anchura del haz de búsqueda. Haz más amplio → más reglas candidatas exploradas.">ⓘ</span>
            </label>
            <input
              v-model.number="params.k_beam"
              type="number" min="1" max="100"
              class="field"
            />
          </div>

          <!-- TOP_POR_CONSECUENTE -->
          <div class="param-group">
            <label class="field-label">
              TOP / CONSECUENTE
              <span class="tip" data-tip="Número máximo de reglas a conservar por cada consecuente.">ⓘ</span>
            </label>
            <input
              v-model.number="params.top_por_consecuente"
              type="number" min="1" max="100"
              class="field"
            />
          </div>

          <!-- MIN_REGLAS_GRUPO -->
          <div class="param-group">
            <label class="field-label">
              MIN_REGLAS_GRUPO
              <span class="tip" data-tip="Mínimo de reglas por grupo para incluirlo en el informe narrativo.">ⓘ</span>
            </label>
            <input
              v-model.number="params.min_reglas_grupo"
              type="number" min="1"
              class="field"
            />
          </div>

          <!-- PAIS -->
          <div class="param-group">
            <label class="field-label">
              PAÍS (festivos)
              <span class="tip" data-tip="Código ISO 3166-1 alfa-2 del país para detección de festivos. Ej: ES, FR, DE.">ⓘ</span>
            </label>
            <input
              v-model="params.pais"
              type="text" maxlength="2" placeholder="ES"
              class="field"
            />
          </div>

          <!-- SUBDIV -->
          <div class="param-group">
            <label class="field-label">
              SUBDIVISIÓN
              <span class="tip" data-tip="Código de comunidad/región para festivos autonómicos. Dejar vacío si no aplica. Ej: CT, PV.">ⓘ</span>
            </label>
            <input
              v-model="params.subdiv"
              type="text" placeholder="vacío = nacional"
              class="field"
            />
          </div>

        </div>
      </section>
    </div>

    <!-- Error general -->
    <div v-if="error" class="error-banner fade-in">
      <span>⚠</span> {{ error }}
    </div>

    <!-- Botón Analizar -->
    <div class="action-row">
      <button
        class="btn-primary btn-analizar"
        :disabled="!archivoSeleccionado || cargando"
        @click="detectarMetrica"
      >
        <span v-if="cargando" class="spinner" />
        <span v-else>Analizar</span>
      </button>
    </div>

    <!-- Modal de confirmación de métrica -->
    <MetricaModal
      v-if="showModal && detectResult"
      :candidatas="detectResult.candidatas"
      :var-tiempo="detectResult.var_tiempo"
      :granularidad-s="detectResult.granularidad_s"
      :cargando="lanzando"
      @cancelar="showModal = false"
      @confirmar="lanzarPipeline"
    />
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import MetricaModal from '@/components/MetricaModal.vue'

const router = useRouter()

// ── Estado local ──
const inputRef = ref(null)
const archivoSeleccionado = ref(null)
const dragging   = ref(false)
const cargando   = ref(false)
const lanzando   = ref(false)
const error      = ref('')
const showModal  = ref(false)
const detectResult = ref(null)

// Parámetros con valores por defecto
const params = reactive({
  min_soporte:       0.005,
  min_confianza:     0.50,
  lift_minimo:       1.5,
  max_prof:          3,
  k_beam:            10,
  top_por_consecuente: 10,
  pais:              'ES',
  subdiv:            null,
  min_reglas_grupo:  2,
})

// ── Handlers de archivo ──
function onDrop(e) {
  dragging.value = false
  const f = e.dataTransfer?.files[0]
  if (f && f.name.endsWith('.csv')) {
    archivoSeleccionado.value = f
  } else {
    error.value = 'El archivo debe ser un CSV (.csv)'
  }
}

function onFileChange(e) {
  const f = e.target.files?.[0]
  if (f) archivoSeleccionado.value = f
}

function limpiarArchivo() {
  archivoSeleccionado.value = null
  if (inputRef.value) inputRef.value.value = ''
}

function formatBytes(bytes) {
  if (bytes < 1024)       return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

// ── Paso 1: detectar métrica ──
async function detectarMetrica() {
  if (!archivoSeleccionado.value) return
  error.value = ''
  cargando.value = true

  try {
    const form = new FormData()
    form.append('csv', archivoSeleccionado.value)
    // Convertir subdiv vacío a null antes de serializar
    const paramsEnvio = { ...params, subdiv: params.subdiv || null }
    form.append('parametros', JSON.stringify(paramsEnvio))

    const { data } = await api.post('/detect-metric', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    detectResult.value = data
    showModal.value = true
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Error al procesar el archivo'
  } finally {
    cargando.value = false
  }
}

// ── Paso 2: lanzar pipeline ──
async function lanzarPipeline(metricaSeleccionada) {
  if (!detectResult.value) return
  lanzando.value = true
  error.value = ''

  try {
    const paramsEnvio = { ...params, subdiv: params.subdiv || null }
    await api.post(`/jobs/${detectResult.value.job_id}/run`, {
      metrica_seleccionada: metricaSeleccionada,
      parametros: paramsEnvio,
    })

    showModal.value = false
    router.push({ name: 'job-status', params: { id: detectResult.value.job_id } })
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Error al lanzar el análisis'
    lanzando.value = false
  }
}
</script>

<style scoped>
/* ── Layout de la página ── */
.home { display: flex; flex-direction: column; gap: 24px; }

.page-header { margin-bottom: 4px; }
.page-title {
  font-family: 'Syne', sans-serif;
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--c-text);
  margin-bottom: 8px;
}
.page-desc { font-size: 0.9rem; color: var(--c-muted); max-width: 560px; line-height: 1.6; }

/* Grid de 2 columnas */
.layout {
  display: grid;
  grid-template-columns: 1fr 1.6fr;
  gap: 20px;
  align-items: start;
}

.section-label {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--c-accent);
  margin-bottom: 16px;
}

/* ── Dropzone ── */
.upload-card { padding: 20px; }

.dropzone {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 180px;
  border: 2px dashed var(--c-border);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
  text-align: center;
  padding: 24px;
}
.dropzone:hover,
.dropzone--over {
  border-color: var(--c-accent);
  background: rgba(249,115,22,0.04);
}
.dropzone--loaded { border-style: solid; border-color: var(--c-accent); }

.drop-icon {
  font-size: 2rem;
  color: var(--c-muted);
  line-height: 1;
  transition: color 0.2s;
}
.drop-icon--ok { color: var(--c-success); }
.dropzone:hover .drop-icon { color: var(--c-accent); }

.drop-msg { font-size: 0.9rem; color: var(--c-text); line-height: 1.5; }
.drop-sub { font-size: 0.78rem; color: var(--c-muted); }

.btn-clear {
  position: absolute;
  top: 10px;
  right: 10px;
  background: var(--c-raised);
  border: 1px solid var(--c-border);
  color: var(--c-muted);
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 0.7rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.15s, color 0.15s;
}
.btn-clear:hover { border-color: var(--c-error); color: var(--c-error); }

/* ── Parámetros ── */
.params-card { padding: 20px; }

.params-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.param-group--full { grid-column: 1 / -1; }

/* ── Acción ── */
.action-row { display: flex; justify-content: flex-end; }

.btn-analizar { padding: 12px 36px; font-size: 0.95rem; }

/* ── Error ── */
.error-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(239,68,68,0.1);
  border: 1px solid rgba(239,68,68,0.3);
  border-radius: 8px;
  color: var(--c-error);
  font-size: 0.85rem;
}

/* ── Spinner ── */
.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }

@media (max-width: 768px) {
  .layout { grid-template-columns: 1fr; }
  .params-grid { grid-template-columns: 1fr; }
}
</style>
