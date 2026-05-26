<template>
  <!-- Overlay del modal de confirmación de métrica -->
  <Teleport to="body">
    <div class="overlay" @click.self="$emit('cancelar')">
      <div class="modal fade-in">
        <!-- Cabecera -->
        <div class="modal-header">
          <span class="modal-icon">⟁</span>
          <div>
            <h2 class="modal-title">¿Qué métrica quieres analizar?</h2>
            <p class="modal-sub">
              Columna temporal detectada:
              <code>{{ varTiempo }}</code>
              <span v-if="granularidadS" class="gran">
                — granularidad {{ granularidadLabel }}
              </span>
            </p>
          </div>
        </div>

        <!-- Candidatas -->
        <div class="candidatas">
          <label
            v-for="c in candidatas"
            :key="c.nombre"
            class="candidata-item"
            :class="{ selected: seleccionada === c.nombre }"
          >
            <input
              type="radio"
              name="metrica"
              :value="c.nombre"
              v-model="seleccionada"
            />
            <div class="candidata-body">
              <div class="candidata-row">
                <span class="candidata-nombre">{{ c.nombre }}</span>
                <span v-if="c.sugerida" class="badge-sugerida">✓ detectada</span>
              </div>
              <span class="candidata-razon">{{ c.razon }}</span>
            </div>
          </label>
        </div>

        <!-- Acciones -->
        <div class="modal-actions">
          <button class="btn-secondary" @click="$emit('cancelar')">
            Cancelar
          </button>
          <button
            class="btn-primary"
            :disabled="!seleccionada || cargando"
            @click="confirmar"
          >
            <span v-if="cargando" class="spinner" />
            <span v-else>Analizar</span>
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  candidatas: Array,
  varTiempo: String,
  granularidadS: Number,
  cargando: Boolean,
})

const emit = defineEmits(['cancelar', 'confirmar'])

// Preseleccionar la candidata sugerida
const seleccionada = ref(
  props.candidatas.find(c => c.sugerida)?.nombre ?? props.candidatas[0]?.nombre ?? ''
)

function confirmar() {
  if (seleccionada.value) emit('confirmar', seleccionada.value)
}

// Granularidad en texto legible
const granularidadLabel = computed(() => {
  const s = props.granularidadS
  if (!s) return ''
  if (s < 60)    return `${s} s`
  if (s < 3600)  return `${Math.round(s / 60)} min`
  if (s < 86400) return `${Math.round(s / 3600)} h`
  return `${Math.round(s / 86400)} días`
})
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(8, 10, 15, 0.75);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 24px;
}

.modal {
  background: var(--c-raised);
  border: 1px solid rgba(249,115,22,0.3);
  border-radius: 16px;
  padding: 28px;
  max-width: 520px;
  width: 100%;
  box-shadow: 0 0 60px rgba(0,0,0,0.6), 0 0 30px rgba(249,115,22,0.08);
}

.modal-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 24px;
}
.modal-icon {
  font-size: 1.8rem;
  color: var(--c-accent);
  line-height: 1;
  flex-shrink: 0;
}
.modal-title {
  font-family: 'Syne', sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--c-text);
  margin-bottom: 4px;
}
.modal-sub {
  font-size: 0.82rem;
  color: var(--c-muted);
}
.modal-sub code {
  font-family: 'JetBrains Mono', monospace;
  color: var(--c-accent);
  background: var(--c-dim);
  padding: 1px 6px;
  border-radius: 4px;
}
.gran {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.78rem;
}

/* Lista de candidatas */
.candidatas {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 24px;
}

.candidata-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: var(--c-card);
  border: 1px solid var(--c-border);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.candidata-item input[type="radio"] { margin-top: 2px; accent-color: var(--c-accent); }
.candidata-item.selected {
  border-color: var(--c-accent);
  background: rgba(249,115,22,0.06);
}

.candidata-body { display: flex; flex-direction: column; gap: 4px; }
.candidata-row  { display: flex; align-items: center; gap: 10px; }
.candidata-nombre {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--c-text);
}
.candidata-razon {
  font-size: 0.78rem;
  color: var(--c-muted);
  line-height: 1.4;
}

.badge-sugerida {
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--c-success);
  background: rgba(34,197,94,0.12);
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(34,197,94,0.3);
}

/* Acciones */
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* Spinner */
.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
