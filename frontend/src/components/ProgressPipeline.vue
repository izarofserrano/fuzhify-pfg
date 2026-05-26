<template>
  <!-- Barra de 3 fases del pipeline con rail horizontal estilo SCADA -->
  <div class="pipeline-wrap">
    <div class="pipeline-rail">

      <template v-for="(fase, i) in fases" :key="fase.id">
        <!-- Línea conectora (entre nodos) -->
        <div v-if="i > 0" class="connector" :class="{ done: estadoFase(fases[i-1].id) === 'done' }" />

        <!-- Nodo de fase -->
        <div class="fase-node" :class="estadoFase(fase.id)">
          <div class="node-circle">
            <!-- Check si completada -->
            <svg v-if="estadoFase(fase.id) === 'done'" viewBox="0 0 16 16" fill="none">
              <path d="M3 8.5l3.5 3.5 6.5-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <!-- Pulso si activa -->
            <span v-else-if="estadoFase(fase.id) === 'active'" class="pulse-dot" />
            <!-- Número si pendiente -->
            <span v-else class="node-num">{{ i + 1 }}</span>
          </div>

          <div class="fase-info">
            <span class="fase-label">{{ fase.label }}</span>
            <span class="fase-pct">{{ fase.pct }}%</span>
          </div>
        </div>
      </template>
    </div>

    <!-- Barra de progreso lineal -->
    <div class="progress-bar-track">
      <div class="progress-bar-fill" :style="{ width: progresoTotal + '%' }" />
    </div>
  </div>
</template>

<script setup>
// Recibe estado y fase_actual del job desde el padre
// fase_actual que envía la API: 'fuzzy' | 'mining' | 'nlg' | null
import { computed, ref, watch } from 'vue'

const props = defineProps({
  estado: String,
  faseActual: { type: String, default: null },
})

const fases = [
  { id: 'fuzzificacion', label: 'Fuzzificación',   pct: 33 },
  { id: 'mineria',       label: 'Minería',          pct: 66 },
  { id: 'nlg',           label: 'Lenguaje natural', pct: 100 },
]

// Estado de cada nodo: 'pending' | 'active' | 'done'
function estadoFase(faseId) {
  if (props.estado === 'completado') return 'done'
  if (props.estado === 'error')      return 'pending'

  const fa = props.faseActual
  if (faseId === 'fuzzificacion') {
    if (fa === 'mining' || fa === 'nlg') return 'done'
    if (fa === 'fuzzy')                  return 'active'
    return 'pending'
  }
  if (faseId === 'mineria') {
    if (fa === 'nlg')    return 'done'
    if (fa === 'mining') return 'active'
    return 'pending'
  }
  if (faseId === 'nlg') {
    if (fa === 'nlg') return 'active'
    return 'pending'
  }
  return 'pending'
}

// Barra lineal: congela el valor en error en lugar de volver a 0
const ultimoProgreso = ref(0)

watch(
  () => ({ estado: props.estado, faseActual: props.faseActual }),
  ({ estado, faseActual }) => {
    if (estado === 'completado') { ultimoProgreso.value = 100; return }
    if (estado === 'error') return  // congela el progreso actual
    const map = { fuzzy: 20, mining: 55, nlg: 80 }
    ultimoProgreso.value = map[faseActual] ?? 0
  },
  { immediate: true },
)

const progresoTotal = computed(() => ultimoProgreso.value)
</script>

<style scoped>
.pipeline-wrap { display: flex; flex-direction: column; gap: 20px; }

/* Rail horizontal con nodos */
.pipeline-rail {
  display: flex;
  align-items: center;
  gap: 0;
}

/* Conector entre nodos */
.connector {
  flex: 1;
  height: 2px;
  background: var(--c-border);
  transition: background 0.4s;
}
.connector.done { background: var(--c-accent); }

/* Nodo */
.fase-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  min-width: 100px;
}

.node-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid var(--c-border);
  background: var(--c-card);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-muted);
  font-family: ui-monospace, monospace;
  font-size: 0.85rem;
  transition: border-color 0.3s, background 0.3s, color 0.3s;
}

/* Fase completada */
.fase-node.done .node-circle {
  border-color: var(--c-accent);
  background: rgba(37,99,235,0.15);
  color: var(--c-accent);
}
.fase-node.done .node-circle svg { width: 18px; height: 18px; }

/* Fase activa */
.fase-node.active .node-circle {
  border-color: var(--c-warn);
  border-width: 3px;
  background: rgba(234,179,8,0.1);
}

/* Punto activo (sin animación) */
.pulse-dot {
  display: block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--c-warn);
}

/* Labels de fase */
.fase-info { text-align: center; }
.fase-label {
  display: block;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--c-muted);
}
.fase-node.done  .fase-label { color: var(--c-accent); }
.fase-node.active .fase-label { color: var(--c-warn); }
.fase-pct {
  display: block;
  font-family: ui-monospace, monospace;
  font-size: 0.65rem;
  color: var(--c-muted);
  margin-top: 2px;
}

/* Barra lineal de progreso */
.progress-bar-track {
  width: 100%;
  height: 4px;
  background: var(--c-border);
  border-radius: 999px;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: #2563EB;
  border-radius: 999px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>
