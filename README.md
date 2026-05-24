# Fuzhify

Sistema de generación automática de resúmenes sobre series temporales basado en lógica difusa y minería de reglas de asociación.

## Requisitos

- Docker Desktop >= 24
- Docker Compose >= 2.24

## Levantar el proyecto en local

### 1. Copiar variables de entorno

```bash
cp backend/.env.example .env
```

Edita `.env` si quieres cambiar usuario/contraseña de PostgreSQL.

### 2. Construir e iniciar los servicios

```bash
docker compose up --build
```

Esto levanta tres servicios:

| Servicio   | URL local                      |
|------------|-------------------------------|
| Backend    | http://localhost:8000          |
| Frontend   | http://localhost:5173          |
| PostgreSQL | localhost:5432                 |

### 3. Verificar que el backend responde

```bash
curl http://localhost:8001/health
# {"status":"ok","version":"0.1.0"}
```

O desde el navegador: http://localhost:8001/health

### 4. Documentación interactiva de la API

http://localhost:8001/docs

### Parar los servicios

```bash
docker compose down
```

Para borrar también el volumen de PostgreSQL:

```bash
docker compose down -v
```

## Estructura del proyecto

```
backend/        FastAPI + lógica del pipeline
frontend/       Vue 3 + Vite + TypeScript
data/           CSVs de entrada/salida (ignorado en git)
notebooks/      Notebooks de referencia (src01–src04)
```
