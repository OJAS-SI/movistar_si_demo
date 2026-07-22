# Movistar Service Intelligence Twin — guion de demostración

**Presenta:** Future Space SA · **Audiencia:** Telefónica / Movistar
**Duración objetivo:** 5:00 · **Presupuesto de locución:** ~700 palabras a 155 ppm
**Idioma de la consola durante la grabación: ES** (conmutador `EN | ES` en la cabecera)

Todas las cifras proceden de la ejecución `full` real de la aplicación
(semilla 20260629 · 2 401 hogares · 41 nodos de acceso · 6 regiones · 576 intervalos con
cadencia de 5 min = **48 horas de tiempo de red**).

**Los textos entre comillas en MAYÚSCULA VERSALITA son literales de pantalla** — están
tomados del catálogo español de la aplicación, así que la locución y la imagen coinciden
palabra por palabra. No los parafrasees al grabar.

---

## Mapa de tiempos

| # | Sección | Entra | Sale | Palabras |
|---|---------|-------|------|----------|
| 1 | Future Space | 0:00 | 0:25 | 58 |
| 2 | La consola — qué está viendo | 0:25 | 1:05 | 95 |
| 3 | Telemetría, intervalo a intervalo | 1:05 | 1:30 | 60 |
| 4 | El problema de Movistar — los tres casos de uso | 1:30 | 2:20 | 118 |
| 5 | Lanzamos la simulación | 2:20 | 2:45 | 58 |
| 6 | Tres fallos, en profundidad | 2:45 | 4:15 | 210 |
| 7 | Cuatro campos, sin aprendizaje previo | 4:15 | 4:40 | 60 |
| 8 | Listo para desplegar | 4:40 | 5:00 | 48 |
| | | | **5:00** | **~707** |

> El español ocupa entre un 15 % y un 20 % más que el inglés para el mismo contenido. El
> guion ya viene recortado para caber en 5:00 a ritmo natural; si al grabar te sobra
> tiempo, alarga la sección 6, que es la que vende.

---

## 1 · Future Space — 0:00–0:25

> **EN PANTALLA** Logotipo Future Space (marca blanca, `image3.svg`) sobre el fondo
> oscuro de la consola. Azul de marca `#1265FF`. Claim: *Donde el futuro se hace presente*.

**LOCUCIÓN**

> Future Space desarrolla Structural Intelligence: una inteligencia artificial que razona
> sobre reglas físicas y topología de red, y no sobre grandes históricos etiquetados.
>
> Lee un fallo como una *forma* sobre el grafo de servicio. Por eso aprende con muy pocos
> datos, y por eso encaja en infraestructuras críticas, donde el dato es escaso, sensible
> o sencillamente no está etiquetado.
>
> Esto es Movistar Service Intelligence, funcionando.

---

## 2 · La consola — 0:25–1:05

> **EN PANTALLA** Pestaña «ANALISTA», escala «REDUCIDA», ejecución completa. El cursor
> recorre cada panel según se nombra.

**LOCUCIÓN**

> Esta es la consola del operador. A la izquierda, «ALERTAS ACTIVAS»: cada fallo que el
> motor ha identificado.
>
> Debajo, fijos, los «INSTRUMENTOS DE HONESTIDAD»: lo que el motor se ha negado a decir.
> «SEÑUELOS QUE DISPARARON», «TASA DE FALSOS POSITIVOS», «INTERVALOS EN CALMA VIGILADOS».
>
> En el centro, «LA FIRMA SOBRE EL GRAFO» y el relato en cuatro tiempos: flujo, formación,
> predicción, prescripción.
>
> A la derecha, «EL VEREDICTO» y el «RECIBO DE DECISIÓN CERTIFICADA»: la afirmación, la
> evidencia, un contraste independiente y la procedencia de cada cifra.

---

## 3 · Telemetría, intervalo a intervalo — 1:05–1:30

> **EN PANTALLA** Pasa el ratón por las tres claves de la leyenda de la cinta; cada una
> muestra su explicación. Después, señala la traza azul del fondo.

**LOCUCIÓN**

> Cada elemento de la red emite un único número por intervalo: descodificadores, gateways
> domésticos, nodos de acceso, rutas de core, fuentes de contenido.
>
> Eso es la traza azul: lo único que el motor puede leer. Sin códigos de error. Sin
> alarmas. Sin etiquetas.
>
> En rojo, «INICIO DEL FALLO». En verde, «EL MOTOR LO IDENTIFICA». La distancia entre
> ambas marcas es la antelación con la que trabaja el operador.

---

## 4 · El problema de Movistar — 1:30–2:20

> **EN PANTALLA** Tres rótulos, uno por caso de uso, con la consola de fondo.

**LOCUCIÓN**

> Tres problemas, del proyecto con Telefónica.
>
> **Uno: nodos de red.** Un fallo en un nodo de acceso aflora como reclamaciones dispersas
> y sin explicación en hogares próximos. Cuando por fin se correlacionan, muchos hogares
> ya están degradados y se están enviando técnicos al sitio equivocado.
>
> **Dos: clientes individuales.** Un hogar solo es visible cuando llama. Su experiencia
> llevaba días deteriorándose.
>
> **Tres: fallos invisibles.** Hay problemas que no llevan ninguna etiqueta, así que la
> herramienta actual no ve nada. Se le pide al cliente que reinicie, o se le sustituye el
> descodificador — y el fallo vuelve, porque nunca estuvo en el equipo.
>
> Un solo mecanismo resuelve los tres: la forma de quién está afectado y qué comparten.

---

## 5 · Lanzamos la simulación — 2:20–2:45

> **EN PANTALLA** Conmuta «REDUCIDA → COMPLETA» (instantáneo). Pulsa reproducir. La cinta
> dura 60 s a 1×; déjala correr por debajo de la sección siguiente.

**LOCUCIÓN**

> Es un modelo sintético de una red española tipo Telefónica. Sin datos de Movistar.
>
> Dos mil cuatrocientos hogares, cuarenta y un nodos de acceso, seis regiones, cuarenta y
> ocho horas de tiempo de red.
>
> Se inyectan veinticuatro fallos, más tres señuelos diseñados para provocar una falsa
> alarma.
>
> Como cada fallo se inyecta, cada respuesta se puntúa contra una verdad conocida.

---

## 6 · Tres fallos, en profundidad — 2:45–4:15

> **EN PANTALLA** Haz clic en cada alerta; deja ver el recibo y la «ACCIÓN RECOMENDADA».

### 6a · Caso 1 — el nodo (0:30)

> **Madrid metro · OLT-2800001-01 · intervalo 80 → 87 · 06:40 → 07:15**

> Madrid metro. Veinte hogares por detrás del nodo de acceso OLT-2800001-01 empiezan a
> desviarse a las 06:40. A las 07:15 el motor ya ha nombrado el nodo: una desviación media
> de siete coma cinco desviaciones típicas por encima de la línea base aprendida de cada
> hogar, y los veinte cuelgan de ese mismo nodo según el mapa de red.
>
> El padre compartido es la atribución: el fallo está en el nodo de acceso, no en ningún
> hogar. Recomendación: inspeccionar el nodo de acceso y su agregación antes de que
> escalen las reclamaciones. Ciento diez minutos de antelación.

### 6b · Caso 2 — el hogar (0:25)

> **Madrid metro · STB-2800002-02-010 · intervalo 207 → 220 · 17:15 → 18:20**

> Un único hogar. Un solo abonado elevado y sostenido, mientras todos sus vecinos en el
> mismo nodo siguen en línea base.
>
> El aislamiento es la atribución: la causa está dentro de este hogar. Recomendación:
> contacto proactivo con el cliente y reconfiguración del gateway. Sin desplazamiento de
> técnico.
>
> Cuatro horas antes de que el cliente lo hubiera notado.

### 6c · Caso 3 — el fallo invisible (0:35)

> **A Coruña · OLT-1500001-01 · intervalo 357 → 365 · día 2, 05:45 → 06:25**

> A Coruña. Cinco hogares, un deterioro recurrente, y ningún código de error en el dato:
> el caso que la herramienta actual no puede ver.
>
> Se simula la sustitución del descodificador en mitad del fallo. La firma no cambia. El
> equipo queda exonerado.
>
> El motor sitúa el fallo en el segmento de acceso con una confianza del noventa y dos por
> ciento. Discriminación de sustitución: cien por cien. Recomendación: investigar el
> segmento y dejar de enviar equipos de repuesto.

---

## 7 · Cuatro campos, sin aprendizaje previo — 4:15–4:40

> **EN PANTALLA** Rótulo con los cuatro campos; vuelve después a «INSTRUMENTOS DE HONESTIDAD».

**LOCUCIÓN**

> Todo lo que acaba de ver sale de cuatro campos por elemento y por intervalo.
>
> `entity_src`, de dónde viene la lectura. `entity_dst`, su padre en la ruta de servicio.
> `timestamp`, qué intervalo. `magnitude`, el deterioro en ese enlace.
>
> Origen y destino son una arista. El tiempo la sitúa en un intervalo. La magnitud es el
> peso. Eso es un grafo ponderado en el tiempo: el mismo registro que NetFlow lleva usando
> veinte años.
>
> Sin entrenamiento. Sin histórico etiquetado. Y aguantó los tres señuelos, con cero
> falsos positivos.

---

## 8 · Listo para desplegar — 4:40–5:00

> **EN PANTALLA** Pestaña «DIRECCIÓN»: 24/24 detectados · 0,0 % falsos positivos ·
> señuelos contenidos 3/3.

**LOCUCIÓN**

> La telemetría ya converge dentro de Telefónica antes de llegar a nosotros. Nos
> conectamos donde ya está recogida: un punto de integración, dos como mucho. Nunca
> elemento a elemento.
>
> Podemos empezar en modo offline, sobre un mes de datos ya almacenados y anonimizados,
> sin integrarnos en sistemas operacionales.
>
> **[PLAZO — ver nota]** y tiene un prototipo funcionando sobre datos de Movistar.

---

## Decisiones antes de grabar

1. **Plazo: ¿4–6 u 8 semanas?** Dijiste *4 a 6 semanas*. La presentación al cliente dice
   **4–8 semanas desde la recepción del dato** (`Movistar_Use_Cases_EN_FINAL.pptx`,
   diapositivas 18 y 20). Contradecir tu propia presentación delante del cliente es peor
   que las dos semanas de más. Recomiendo decir **«de cuatro a ocho semanas desde la
   recepción del dato»**, o corregir la presentación primero.

2. **«Tiempo real»: con cuidado.** La presentación plantea la Opción 1 como *offline,
   sobre ~1 mes de histórico*, y la Opción 2 como *(casi) tiempo real*. El guion dice por
   eso **«intervalo a intervalo»** y no «tiempo real». Si quieres la expresión, usa
   **«casi tiempo real»**; «tiempo real» a secas no es defendible para la Opción 1.

3. **La confianza no es una probabilidad.** Si preguntan: es una puntuación ponderada
   sobre tres proporciones medidas — concentración, fuerza de la desviación y encaje
   topológico. No presentes el 92 % como «92 % de probabilidad».

4. **Di «sintético» en voz alta** (está en §5). La consola lleva el distintivo «DEMO
   SINTÉTICA»; la locución debe coincidir, o la sala puede creer que se ha ejecutado sobre
   su red.

5. **Números en español.** Decimales con coma al locutar: «siete coma cinco», «cero coma
   cero por ciento». La consola ya escribe `7.5` con punto — es cosmético, pero si te
   molesta en cámara, dímelo y lo cambio a coma en el catálogo español.

---

## Bloque de datos — regenerar si cambia la semilla

```
ejecución: full · semilla 20260629 · 2401 hogares · 41 nodos de acceso · 6 regiones
           576 intervalos @ 300 s = 48 h de tiempo de red
totales:   24 fallos · 24/24 detectados · falsos positivos 0,0 % (0 de 89 intervalos en calma)
           señuelos disparados 0/3 · autoprueba PASS · antelación media 44,4 min

UC1  OLT-2800001-01      Madrid metro   acceso/clúster   20 hogares
     inicio 80 (06:40) → identificado 87 (07:15)    antelación 110 min   conf 77 %   7,5σ
UC2  STB-2800002-02-010  Madrid metro   hogar/individual  1 hogar
     inicio 207 (17:15) → identificado 220 (18:20)  antelación 255 min   conf 73 %   6,9σ
UC3  OLT-1500001-01      A Coruña       acceso/clúster    5 hogares
     inicio 357 (05:45 +1d) → identificado 365 (06:25 +1d)  antelación 75 min  conf 92 %  8,8σ
     discriminación de sustitución de descodificador 100 %
```

Regenerar con la aplicación en :8001 —
`curl -s "http://127.0.0.1:8001/api/runs/<run_id full>/console?lang=es"`.

---

## Literales de pantalla en español (para que locución e imagen coincidan)

| Elemento | Texto en pantalla |
|---|---|
| Pestañas | ANALISTA · DIRECCIÓN · MAPA |
| Escala | REDUCIDA · COMPLETA |
| Rail | ALERTAS ACTIVAS · LÍMITE DE COMPETENCIA |
| Honestidad | INSTRUMENTOS DE HONESTIDAD · SEÑUELOS QUE DISPARARON · TASA DE FALSOS POSITIVOS · INTERVALOS EN CALMA VIGILADOS |
| Centro | LA FIRMA SOBRE EL GRAFO · Flujo · Formación · Predicción · Prescripción |
| Derecha | EL VEREDICTO · MEDIDO FRENTE A LA VERDAD DE REFERENCIA · RECIBO DE DECISIÓN CERTIFICADA · ACCIÓN RECOMENDADA |
| Leyenda cinta | inicio del fallo · transitorio benigno · el motor lo identifica |
| Métricas | Hogares afectados · Antelación · Localización · Atribución de capa |
| Cabecera | Centro de Operaciones de Experiencia de Cliente |

Acciones recomendadas, literales del motor en español:

- **Clúster/acceso** — «inspeccionar el nodo de acceso y su agregación antes de que
  escalen las reclamaciones»
- **Hogar aislado** — «contacto proactivo con el cliente y reconfiguración del gateway,
  sin desplazamiento de técnico»
- **Ruta de core** — «investigar la ruta de transporte de core que da servicio a los
  hogares afectados»
- **Fuente de contenido** — «investigar la fuente de contenido y su ruta de entrega»
