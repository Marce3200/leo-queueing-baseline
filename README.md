# leo-queueing-baseline

Modelo de colas del recorrido del mensaje de emergencia, desde el nodo emisor hasta la estación terrena, para la arquitectura de red mesh LoRa con backhaul satelital LEO.

Corresponde a la etapa analítica del Seminario de Grado I. El modelo se resuelve de dos formas independientes: analíticamente en este repositorio y con JMVA (Java Modelling Tools), cuya coincidencia constituye la validación cruzada.

## Estructura

```
modelos/       archivos .jmva del modelo construido en JMT
scripts/       solución analítica, barridos y figuras
figuras/       figuras generadas
resultados/    planillas de validación y de barridos, en CSV
```

## Uso

```
python scripts/baseline.py
```

Requiere numpy y matplotlib.

## Modelo

Red abierta de cuatro estaciones con una clase de mensajes.

| Estación | Tipo | Demanda de servicio | Origen |
| --- | --- | --- | --- |
| Nodo emisor | Delay | 0,3287 s | Tiempo en aire, SF9 con 50 B |
| Canal mesh | Cola de un servidor | 0,5917 s | 1,8 saltos promedio |
| Enlace de subida | Cola de un servidor | 162,11 s / N | SF12 con 50 B sobre disponibilidad de 1,42 % |
| Descarga a estación terrena | Delay | 0,0208 s | 25 B a 9,6 kbps |

N es el número de satélites de la constelación.

## Supuestos declarados

1. La intermitencia del enlace satelital se representa mediante una tasa de servicio efectiva, es decir, el tiempo en aire dividido por la disponibilidad. El modelo no representa las ventanas de contacto de forma explícita, por lo que entrega una cota inferior de la latencia: distribuye la espera de ventana de manera uniforme en lugar de concentrarla al cierre de cada contacto.
2. La disponibilidad escala linealmente con el número de satélites. Este supuesto debe contrastarse con las ventanas reales del propagador orbital.
3. El buffer del gateway no descarta mensajes por antigüedad. El refinamiento con capacidad finita y bloqueo aguas arriba se resuelve por simulación, fuera del alcance de este script.
4. La tasa del enlace de bajada se toma en el extremo conservador del rango declarado (9,6 kbps).

## Salidas

| Archivo | Contenido |
| --- | --- |
| `resultados/validacion_jmva.csv` | Error relativo entre el cálculo analítico y JMVA en los puntos de control |
| `resultados/umbrales_constelacion.csv` | Tasa de saturación y cruce del plazo de utilidad operativa por constelación |
| `resultados/estabilidad_regimenes.csv` | Estabilidad de cada régimen de tráfico para cada constelación |
| `resultados/barrido_N1.csv` | Barrido completo con un satélite |
| `figuras/fig10_utilizacion_constelaciones.png` | Utilización frente a tasa de llegada |
| `figuras/fig11_residencia_constelaciones.png` | Tiempo de residencia frente a tasa de llegada |
| `figuras/fig12_clientes_constelaciones.png` | Número medio de mensajes frente a tasa de llegada |
