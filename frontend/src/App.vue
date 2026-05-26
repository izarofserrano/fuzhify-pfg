<template>
  <div class="app-shell">
    <!-- Barra de navegación superior -->
    <header class="nav-bar">
      <div class="nav-inner">
        <!-- Logo / marca -->
        <router-link to="/" class="nav-brand">
          <span class="brand-icon">◈</span>
          <span class="brand-name">Fuzhify</span>
          <span class="brand-tag">Análisis difuso</span>
        </router-link>

        <!-- Links de navegación -->
        <nav class="nav-links">
          <router-link to="/" class="nav-link" :class="{ active: $route.path === '/' }">
            Nuevo análisis
          </router-link>
          <router-link to="/comparador" class="nav-link" :class="{ active: $route.path === '/comparador' }">
            Comparador
          </router-link>
        </nav>
      </div>
    </header>

    <!-- Contenido principal -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
// App.vue: shell de la aplicación con nav y router-view
</script>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ── Barra de navegación ── */
.nav-bar {
  position: sticky;
  top: 0;
  z-index: 40;
  background: #1E293B;
  border-bottom: 1px solid var(--c-border);
}
.nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
}
.brand-icon {
  font-size: 1.4rem;
  color: var(--c-accent);
  line-height: 1;
}
.brand-name {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--c-text);
  letter-spacing: 0.02em;
}
.brand-tag {
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--c-muted);
  padding: 2px 8px;
  border: 1px solid var(--c-border);
  border-radius: 999px;
}

.nav-links { display: flex; gap: 4px; }
.nav-link {
  padding: 6px 14px;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--c-muted);
  text-decoration: none;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}
.nav-link:hover  { color: var(--c-text); background: var(--c-raised); }
.nav-link.active { color: var(--c-accent); background: var(--c-dim); }

/* ── Contenido ── */
.main-content {
  flex: 1;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 32px 24px;
}

/* ── Transición de página ── */
.page-enter-active,
.page-leave-active { transition: opacity 0.18s ease, transform 0.18s ease; }
.page-enter-from   { opacity: 0; transform: translateY(8px); }
.page-leave-to     { opacity: 0; transform: translateY(-4px); }
</style>
