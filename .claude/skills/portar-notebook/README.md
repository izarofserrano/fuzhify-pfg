# Skill: portar-notebook

Skill personalizada para Claude Code que estandariza la migración de notebooks Jupyter a módulos Python importables **preservando la lógica de negocio**.

## Cómo instalarla en Claude Code

1. Copia la carpeta `portar-notebook/` completa a uno de estos directorios:

   - **Para el proyecto Fuzhify (recomendado):**
     ```
     <raíz del repo>/.claude/skills/portar-notebook/
     ```
     Así la skill viaja con el repo y queda en el `git log` de tu TFG.

   - **Para uso global en tu máquina:**
     ```
     ~/.claude/skills/portar-notebook/
     ```

2. Reinicia la sesión de Claude Code (`Ctrl+C` y volver a abrir).

3. Verifica que Claude la ha detectado pidiendo: *"¿Qué skills tienes disponibles?"* — debería listar `portar-notebook`.

## Cuándo se dispara

Automáticamente cuando uses frases del tipo:

- "Migra el notebook X a `core/Y/`"
- "Porta este `.ipynb` a un módulo importable"
- "Convierte el notebook en CLI / paquete / módulo"

Para los prompts del `PLAN_MIGRACION.md`, la skill se activará sola en las fases 1, 2, 3 y 4.

## Cómo evolucionarla

La skill es un fichero Markdown. Cuando hagas la fase 1 con Claude Code y veas que algo no encaja con tu flujo, edita `SKILL.md` directamente. Patrones que merecen volver a la skill:

- Si Claude Code intenta refactorizar más de la cuenta, refuerza la sección "Anti-patrones".
- Si los tests de paridad fallan por orden de filas/columnas, añade el caso a la sección "Test de paridad".
- Si descubres una eliminación nueva permitida (ej. `%load_ext autoreload`), añádela a la lista del paso 3.

## Cómo NO usarla

- No la uses para refactorizaciones puras (renombrar, reordenar, dividir funciones). Eso es otra tarea.
- No la uses para *escribir* notebooks nuevos. Solo para portar los existentes.
