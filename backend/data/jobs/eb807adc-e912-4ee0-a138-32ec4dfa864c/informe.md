# Resumen de comportamiento — 3600.csv

**Métrica analizada:** Intensidad  
**Total de reglas analizadas:** 32

> ### 📖 Niveles de la métrica analizada (intensidad) 
> Escala desde **excepcionalmente bajo** ⚪ hasta **excepcionalmente alto** 🔴, calculada a partir de la desviación sobre la media histórica del propio sensor.
>
> Cuando el patrón es *muy diferenciado* del comportamiento normal se describe *'de forma notable'* o *'muy marcada'*. Cuando es solo una *tendencia*, se dice así.
## Visualizaciones

### Mapa de calor hora × día de la semana
![Mapa de calor hora x día](data/3600.csv_heatmap.png)

### Reglas por fuerza de asociación (lift)
![Barras lift](data/3600.csv_barras_lift.png)

### Soporte vs Confianza
![Scatter soporte-confianza](data/3600.csv_scatter.png)

### Resumen por categoría
![Tabla consecuentes](data/3600.csv_tabla_consecuentes.png)

## ¿Cómo se comporta **intensidad** a lo largo del día?
> Esta sección resume el comportamiento de **intensidad** en lenguaje sencillo, sin tecnicismos.

De madrugada (0–6 h), el intensidad es **bajo** 🔵. Al llegar la mañana (7–13 h), el intensidad se mantiene en niveles **bajo** 🔵. Por la tarde (14–20 h), el intensidad sube a niveles **excepcionalmente alto (un pico)** 🔴, especialmente entre semana, con calma en fin de semana. Al caer la noche (21–23 h), el intensidad cae a un nivel **moderado** 🟢.

Los **fines de semana** el intensidad se reduce respecto a los días laborables, aunque sin llegar a invertir el patrón general.

## Análisis por franja horaria

Detalle de los patrones detectados, organizados por momento del día. Cada punto indica el nivel de intensidad más probable en ese contexto, junto con la confianza y el lift de la regla.

### Madrugada (0–6 h)

- 🟢 **Media** de forma notable: las 0 h en los sábados (confianza 57 %, lift 2.8)
- 🔵 **Baja** de forma notable: las 3 h en los domingos (confianza 65 %, lift 3.0)
- 🔵 **Baja** de forma notable: las 0 h (confianza 59 %, lift 2.7)
- 🔵 **Baja** de forma notable: las 1 h (confianza 54 %, lift 2.5)
- 🔵 **Baja** de forma notable: las 6 h (confianza 53 %, lift 2.4)
- 🔵 **Baja** de forma notable: la madrugada (0–6 h) en los sábados (confianza 50 %, lift 2.3)
- 🟣 **Muy baja** de forma notable: la madrugada (0–6 h) (confianza 52 %, lift 2.8)

### Mañana (7–13 h)

- 🟡 **Alta** de forma notable: las 10 h en el año 2024 (confianza 62 %, lift 2.7)
- 🟡 **Alta** de forma notable: las 13 h en fin de semana (confianza 58 %, lift 2.5)
- 🟡 **Alta** de forma notable: las 11 h (confianza 55 %, lift 2.4)
- 🟡 **Alta** de forma notable: las 12 h (confianza 54 %, lift 2.3)
- 🟢 **Media** de forma notable: las 9 h en los sábados (confianza 55 %, lift 2.8)
- 🟢 **Media** de forma notable: las 10 h en fin de semana (confianza 51 %, lift 2.6)
- 🔵 **Baja** de forma muy marcada: las 7 h en fin de semana (confianza 81 %, lift 3.7)
- 🔵 **Baja** de forma muy marcada: las 9 h en los domingos (confianza 77 %, lift 3.5)

### Tarde (14–20 h)

- 🔴 **Excepcionalmente alta (outlier superior)** de forma muy marcada: las 18 h en los martes (confianza 59 %, lift 6.2)
- 🔴 **Excepcionalmente alta (outlier superior)** de forma muy marcada: las 18 h en los jueves (confianza 58 %, lift 6.1)
- 🔴 **Excepcionalmente alta (outlier superior)** de forma muy marcada: las 18 h en los miércoles (confianza 58 %, lift 6.0)
- 🔴 **Excepcionalmente alta (outlier superior)** de forma muy marcada: las 18 h en los lunes (confianza 52 %, lift 5.5)
- 🔴 **Excepcionalmente alta (outlier superior)** de forma muy marcada: las 14 h en días laborables (confianza 51 %, lift 5.3)
- 🟠 **Muy alta** de forma muy marcada: la tarde (14–20 h) en días laborables (confianza 56 %, lift 3.3)
- 🟠 **Muy alta** de forma muy marcada: la tarde (14–20 h) en el año 2024 (confianza 52 %, lift 3.1)
- 🟠 **Muy alta** de forma notable: las 14 h (confianza 50 %, lift 3.0)
- 🟡 **Alta** de forma notable: las 19 h en fin de semana (confianza 56 %, lift 2.4)
- 🟡 **Alta** de forma notable: las 20 h en el año 2024 (confianza 52 %, lift 2.2)
- 🟢 **Media** de forma notable: las 16 h en fin de semana (confianza 56 %, lift 2.8)

### Noche (21–23 h)

- 🟡 **Alta** de forma notable: las 21 h en el año 2024 (confianza 58 %, lift 2.5)
- 🟢 **Media** de forma muy marcada: las 23 h en el año 2024 (confianza 62 %, lift 3.1)
- 🟢 **Media** de forma notable: las 22 h (confianza 54 %, lift 2.7)
- 🔵 **Baja** de forma notable: las 23 h en el año 2025 (confianza 57 %, lift 2.6)

---

## Apéndice — Análisis por nivel de intensidad


> ### 📖 Glosario técnico (apéndice)
> * **Confianza:** probabilidad (0–100 %) de que el patrón sea cierto cuando se da el contexto. Confianza 80 % significa que, en ese contexto, el la métrica se comporta así 8 de cada 10 veces.
> * **Lift:** cuántas veces más probable es el evento respecto al azar. Lift 5.0 significa que el patrón es 5 veces más frecuente en ese contexto que en el resto del tiempo.
> * **Outlier inferior/superior:** valor más allá de 2 desviaciones típicas de la media histórica del sensor.

*Mismas reglas organizadas por nivel de **intensidad** (de mayor a menor valor).*

### 🔴 Intensidad excepcionalmente alta (outlier superior)
*5 reglas — agrupadas en 2 contextos* | confianza media: 55 %, lift medio: 5.8 

En el contexto de las 18 h, la intensidad tiende a ser excepcionalmente alta (outlier superior), especialmente en los martes (59 %), los jueves (58 %), los miércoles (58 %) y los lunes (52 %). Este patrón se observa con una confianza media del 57 % y un lift máximo de 6.2.

A las 14 h en días laborables, la intensidad tiende a ser excepcionalmente alta (outlier superior) de forma muy marcada (confianza 51 %, lift 5.3).

### 🟠 Intensidad muy alta
*3 reglas — agrupadas en 2 contextos* | confianza media: 53 %, lift medio: 3.1 

En el contexto de la tarde (14–20 h), la intensidad tiende a ser muy alta, especialmente en días laborables (56 %) y el año 2024 (52 %). Este patrón se observa con una confianza media del 54 % y un lift máximo de 3.3.

A las 14 h, la intensidad tiende a ser muy alta de forma notable (confianza 50 %, lift 3.0).

### 🟡 Intensidad alta
*7 reglas — agrupadas en 7 contextos* | confianza media: 56 %, lift medio: 2.4 

A las 10 h en el año 2024, la intensidad tiende a ser alta de forma notable (confianza 62 %, lift 2.7).

A las 21 h en el año 2024, la intensidad tiende a ser alta de forma notable (confianza 58 %, lift 2.5).

A las 13 h en fin de semana, la intensidad tiende a ser alta de forma notable (confianza 58 %, lift 2.5).

A las 19 h en fin de semana, la intensidad tiende a ser alta de forma notable (confianza 56 %, lift 2.4).

A las 11 h, la intensidad tiende a ser alta de forma notable (confianza 55 %, lift 2.4).

A las 12 h, la intensidad tiende a ser alta de forma notable (confianza 54 %, lift 2.3).

A las 20 h en el año 2024, la intensidad tiende a ser alta de forma notable (confianza 52 %, lift 2.2).

### 🟢 Intensidad media
*6 reglas — agrupadas en 6 contextos* | confianza media: 56 %, lift medio: 2.8 

A las 23 h en el año 2024, la intensidad tiende a ser media de forma muy marcada (confianza 62 %, lift 3.1).

A las 0 h en los sábados, la intensidad tiende a ser media de forma notable (confianza 57 %, lift 2.8).

A las 16 h en fin de semana, la intensidad tiende a ser media de forma notable (confianza 56 %, lift 2.8).

A las 9 h en los sábados, la intensidad tiende a ser media de forma notable (confianza 55 %, lift 2.8).

A las 22 h, la intensidad tiende a ser media de forma notable (confianza 54 %, lift 2.7).

A las 10 h en fin de semana, la intensidad tiende a ser media de forma notable (confianza 51 %, lift 2.6).

### 🔵 Intensidad baja
*10 reglas — agrupadas en 10 contextos* | confianza media: 60 %, lift medio: 2.8 

A las 7 h en fin de semana, la intensidad tiende a ser baja de forma muy marcada (confianza 81 %, lift 3.7).

A las 9 h en los domingos, la intensidad tiende a ser baja de forma muy marcada (confianza 77 %, lift 3.5).

A las 3 h en los domingos, la intensidad tiende a ser baja de forma notable (confianza 65 %, lift 3.0).

A las 0 h, la intensidad tiende a ser baja de forma notable (confianza 59 %, lift 2.7).

A las 23 h en el año 2025, la intensidad tiende a ser baja de forma notable (confianza 57 %, lift 2.6).

A las 1 h, la intensidad tiende a ser baja de forma notable (confianza 54 %, lift 2.5).

A las 6 h, la intensidad tiende a ser baja de forma notable (confianza 53 %, lift 2.4).

En agosto en el año 2025, la intensidad tiende a ser baja de forma notable (confianza 52 %, lift 2.4).

En los domingos en agosto, la intensidad tiende a ser baja de forma notable (confianza 52 %, lift 2.4).

Durante la madrugada (0–6 h) en los sábados, la intensidad tiende a ser baja de forma notable (confianza 50 %, lift 2.3).

### 🟣 Intensidad muy baja
*1 regla — agrupadas en 1 contexto* | confianza media: 52 %, lift medio: 2.8 

Durante la madrugada (0–6 h), la intensidad tiende a ser muy baja de forma notable (confianza 52 %, lift 2.8).

---

## Estadísticas globales del análisis

| Métrica | Valor |
|---|---|
| Reglas totales | 32 |
| Consecuentes únicos | 6 |
| Soporte medio | 0.0565 |
| Confianza media | 56.7 % |
| Lift medio | 3.21 |
| Lift máximo | 6.21 |