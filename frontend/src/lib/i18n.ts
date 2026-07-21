/**
 * The console in English or Spanish.
 *
 * Two kinds of text share this screen and they are translated in different places.
 *
 *   The engine's sentences - headlines, health bands, recommended actions, receipts -
 *   are composed from live values by si_core and rendered by a catalogue in si_api.
 *   The client never translates those; it asks for a language and displays what comes
 *   back. That is why every API call carries `lang`.
 *
 *   The console's own chrome - labels, column headings, legends, tooltips - is this
 *   file. It never contains a measurement, so it can be a plain dictionary.
 *
 * The split matters: a number the engine measured must not pass through a translation
 * table on its way to the screen, or the demo can no longer claim its console and its
 * scorecard agree.
 */

export const LANGS = ['en', 'es'] as const
export type Lang = (typeof LANGS)[number]

const STORAGE_KEY = 'movistar-si.lang'

/** The language to open in: the operator's last choice, else the browser's, else EN. */
export function initialLang(): Lang {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY)
    if (saved && (LANGS as readonly string[]).includes(saved)) return saved as Lang
  } catch {
    /* private browsing or storage disabled; fall through to the browser's preference */
  }
  const preferred = (window.navigator.languages ?? [window.navigator.language]).find((tag) =>
    (LANGS as readonly string[]).includes(tag?.split('-')[0]),
  )
  return (preferred?.split('-')[0] as Lang) ?? 'en'
}

export function rememberLang(lang: Lang): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, lang)
  } catch {
    /* nothing to do: the choice simply will not survive a reload */
  }
}

/**
 * The console's own words. Keys read as what the string is for, not as the English of
 * it, so changing the English wording never means renaming a key.
 */
const STRINGS = {
  // ----- header and run controls -----
  'header.scale': ['Scale', 'Escala'],
  'header.scale.tiny': ['Tiny', 'Reducida'],
  'header.scale.full': ['Full', 'Completa'],
  'header.language': ['Language', 'Idioma'],
  'header.subtitle': ['Customer Experience Operations Center', 'Centro de Operaciones de Experiencia de Cliente'],
  'header.synthetic': ['Synthetic demo', 'Demo sintética'],
  'header.engine': ['SI engine', 'Motor SI'],
  'header.engine.running': ['running', 'ejecutando'],
  'header.engine.live': ['live', 'activo'],
  'header.scale.tiny.tip': [
    'A small network, a short run — the whole story in a second.',
    'Una red pequeña, una ejecución corta: toda la historia en un segundo.',
  ],
  'header.scale.full.tip': [
    'The full six-region network. Slower to compute.',
    'La red completa de seis regiones. Más lenta de calcular.',
  ],
  'alerts.formingNotResolved': ['Shape forming — not yet resolved', 'Firma formándose: aún sin resolver'],

  // ----- the closed vocabularies, as they read on a chip -----
  // These live here rather than in format.ts because they are wording, and format.ts
  // deliberately holds no language. The engine's own layer/shape codes are unchanged.
  'layerLabel.home': ['Home / Wi-Fi', 'Hogar / Wi-Fi'],
  'layerLabel.access': ['Access / aggregation', 'Acceso / agregación'],
  'layerLabel.core': ['Core / transport', 'Core / transporte'],
  'layerLabel.content': ['Content / CDN', 'Contenido / CDN'],
  'layerLabel.unresolved': ['Unresolved', 'Sin resolver'],
  'shapeLabel.single': ['Single (isolated home)', 'Individual (hogar aislado)'],
  'shapeLabel.cluster': ['Cluster (behind one node)', 'Clúster (tras un mismo nodo)'],
  'shapeLabel.path': ['Path (along a route)', 'Camino (a lo largo de una ruta)'],
  'shapeLabel.source': ['Source (one origin, many homes)', 'Fuente (un origen, muchos hogares)'],
  'shapeLabel.none': ['No shape', 'Sin firma'],

  // ----- the shape-graph legend -----
  'graph.impaired': ['impaired home', 'hogar afectado'],
  'graph.drifting': ['just starting to drift', 'empezando a desviarse'],
  'graph.healthyPeer': ['healthy peer', 'vecino sano'],
  'graph.namedElement': ['the named element', 'el elemento identificado'],

  // ----- tabs -----
  'tab.analyst': ['Analyst', 'Analista'],
  'tab.map': ['Map', 'Mapa'],
  'tab.management': ['Management', 'Dirección'],

  // ----- the alert rail -----
  'alerts.active': ['Active alerts', 'Alertas activas'],
  'alerts.homes': ['homes', 'hogares'],
  'alerts.home': ['home', 'hogar'],
  'alerts.competenceBoundary': ['Competence boundary', 'Límite de competencia'],
  'alerts.abstainedAt': ['abstained at interval', 'abstención en el intervalo'],

  // ----- honest instruments -----
  'honest.title': ['Honest instruments', 'Instrumentos de honestidad'],
  'honest.subtitle': [
    'Measured over the whole run, against ground truth the engine never sees.',
    'Medido sobre toda la ejecución, frente a una verdad de referencia que el motor nunca ve.',
  ],
  'honest.decoysFired': ['Decoys that fired', 'Señuelos que dispararon'],
  'honest.falsePositiveRate': ['False-positive rate', 'Tasa de falsos positivos'],
  'honest.quietIntervals': ['Quiet intervals watched', 'Intervalos en calma vigilados'],

  // ----- the verdict panel -----
  'verdict.element': ['element', 'elemento'],
  'verdict.layer': ['layer', 'capa'],
  'verdict.shape': ['shape', 'firma'],
  'verdict.region': ['region', 'región'],
  'verdict.confidence': ['confidence', 'confianza'],
  'verdict.caught': ['caught', 'detectado'],
  'verdict.beforeSurfacing': ['before it would surface', 'antes de que aflorara'],
  'verdict.theCall': ['The call', 'El veredicto'],
  'verdict.shapeOnGraph': ['The shape on the graph', 'La firma sobre el grafo'],
  'verdict.detectionNarrative': ['Detection narrative', 'Relato de la detección'],
  'verdict.namedAt': ['Named at interval', 'Identificado en el intervalo'],

  // ----- measured against ground truth -----
  'measured.title': ['Measured against ground truth', 'Medido frente a la verdad de referencia'],
  'measured.homesAffected': ['Homes affected', 'Hogares afectados'],
  'measured.leadTime': ['Lead time', 'Antelación'],
  'measured.localization': ['Localization', 'Localización'],
  'measured.layerAttribution': ['Layer attribution', 'Atribución de capa'],

  // ----- the receipt -----
  'receipt.title': ['Certified-decision receipt', 'Recibo de decisión certificada'],
  'receipt.claim': ['Claim', 'Afirmación'],
  'receipt.evidence': ['Evidence', 'Evidencia'],
  'receipt.check': ['Check', 'Contraste'],
  'receipt.provenance': ['Provenance', 'Procedencia'],
  'receipt.confidence': ['Confidence', 'Confianza'],

  // ----- recommended action -----
  'action.title': ['Recommended action', 'Acción recomendada'],
  'action.footer': [
    'These are the actions the verdict licenses. Nothing here dispatches to a real network.',
    'Estas son las acciones que autoriza el veredicto. Nada de esto se envía a una red real.',
  ],


  // ----- the transport bar -----
  'transport.interval': ['Interval', 'Intervalo'],
  'transport.play': ['Play the run', 'Reproducir la ejecución'],
  'transport.pause': ['Pause', 'Pausar'],
  'transport.reset': ['Back to the first interval', 'Volver al primer intervalo'],
  'transport.speed': ['Playback speed', 'Velocidad de reproducción'],
  'transport.computing': ['Computing the run…', 'Calculando la ejecución…'],

  // ----- the ribbon legend, and what each mark proves -----
  'legend.faultOnset': ['fault onset', 'inicio del fallo'],
  'legend.benignTransient': ['benign transient', 'transitorio benigno'],
  'legend.engineNames': ['engine names it', 'el motor lo identifica'],
  'legend.faultOnset.tip': [
    'Ground truth: the interval a real fault actually began. The engine never sees these ' +
      'marks — it reads only the magnitude trace behind them.',
    'Verdad de referencia: el intervalo en que empezó realmente un fallo. El motor nunca ve ' +
      'estas marcas: solo lee la traza de magnitud que hay detrás.',
  ],
  'legend.benignTransient.tip': [
    'Ground truth: a short, benign disturbance — a prime-time load spike, a one-off home ' +
      'glitch, an isolated reboot. It is not a fault, and the engine must not fire on it. ' +
      'No green mark ever appears beside one; that is what the false-positive rate is counting.',
    'Verdad de referencia: una perturbación breve y benigna — un pico de carga en hora punta, ' +
      'un fallo puntual en un hogar, un reinicio aislado. No es un fallo y el motor no debe ' +
      'dispararse. Nunca aparece una marca verde junto a una: eso es lo que mide la tasa de ' +
      'falsos positivos.',
  ],
  'legend.engineNames.tip': [
    'The engine speaking: the interval it committed to naming the element responsible. It ' +
      'lands after the red mark by design, because evidence has to accumulate — but still ' +
      'before the fault would surface to a customer. That second gap is the lead time.',
    'El motor hablando: el intervalo en que se comprometió a nombrar el elemento responsable. ' +
      'Llega después de la marca roja por diseño, porque la evidencia debe acumularse, pero ' +
      'aun así antes de que el fallo aflorara a un cliente. Esa segunda distancia es la antelación.',
  ],

  // ----- the individual marks on the ribbon -----
  'mark.faultOnset': ['Fault onset (ground truth)', 'Inicio del fallo (verdad de referencia)'],
  'mark.faultOnset.body': [
    'truly begins at interval',
    'empieza realmente en el intervalo',
  ],
  'mark.faultOnset.tail': [
    'The engine is never told — it has to find this in the four-field trace alone.',
    'Al motor nunca se le dice: tiene que encontrarlo solo en la traza de cuatro campos.',
  ],
  'mark.benign': ['Benign transient (ground truth)', 'Transitorio benigno (verdad de referencia)'],
  'mark.benign.body': ['at interval', 'en el intervalo'],
  'mark.benign.tail': [
    'Not a fault. The engine must stay silent here — and no green mark ever follows one.',
    'No es un fallo. El motor debe permanecer en silencio aquí, y nunca le sigue una marca verde.',
  ],
  'mark.named': ['The engine speaking: named', 'El motor hablando: identificó'],
  'mark.named.body': ['at interval', 'en el intervalo'],
  'mark.named.tail': [
    'intervals after the fault began — the wait is evidence accumulating, and it still ' +
      'lands before the fault would surface to a customer.',
    'intervalos después de que empezara el fallo: la espera es evidencia acumulándose, y aun ' +
      'así llega antes de que el fallo aflorara a un cliente.',
  ],

  'measured.boxSwap': ['Box-swap discrimination', 'Discriminación de sustitución del set-top box'],
  'measured.boxSwap.body': [
    'The signature survives a set-top-box replacement, so the box is exonerated and the futile swap is avoided.',
    'La firma sobrevive a la sustitución del set-top box, de modo que el equipo queda exonerado y se evita la sustitución inútil.',
  ],

  // ----- the watching state (before anything is named) -----
  'watch.formingTitle': [
    'A shape is forming — the engine has not yet resolved it',
    'Se está formando una firma: el motor todavía no la ha resuelto',
  ],
  'watch.title': ['Watching the network', 'Vigilando la red'],
  'watch.records': ['four-field records this interval', 'registros de cuatro campos en este intervalo'],
  'watch.meanMagnitude': ['mean magnitude', 'magnitud media'],
  'watch.peak': ['peak', 'pico'],
  'watch.allowedToSee': ['What the engine is allowed to see', 'Lo que el motor puede ver'],
  'watch.allowedToSee.body': [
    'Four fields per record — no error codes, no alarms, no labels. It learns each edge\'s own baseline from the history it observes, and watches the graph for structure.',
    'Cuatro campos por registro: sin códigos de error, sin alarmas, sin etiquetas. Aprende la línea base de cada enlace a partir del histórico que observa y vigila la estructura del grafo.',
  ],
  'watch.drifting': [
    'Something is drifting above baseline right now, but it has not cleared the dwell gate — so nothing is claimed.',
    'Algo se está desviando por encima de la línea base ahora mismo, pero no ha superado el umbral de permanencia, así que no se afirma nada.',
  ],
  'watch.nothingYet': ['Nothing has departed from baseline yet.', 'Todavía nada se ha desviado de la línea base.'],
  'watch.nextVerdict': ['The next verdict lands at interval', 'El siguiente veredicto llega en el intervalo'],
  'watch.holdingFire': ['Holding fire', 'Sin disparar'],
  'watch.decoysFired': ['Decoys fired', 'Señuelos disparados'],
  'watch.falsePositives': ['False positives', 'Falsos positivos'],
  'watch.holdingFire.body': [
    'Benign disturbances — a prime-time surge, a one-off glitch, a reboot — are injected deliberately. An engine that fired on them would be useless in an operations room, so what it ignores is measured just as carefully as what it catches.',
    'Las perturbaciones benignas — un pico en hora punta, un fallo puntual, un reinicio — se inyectan a propósito. Un motor que disparase con ellas sería inútil en una sala de operaciones, así que lo que ignora se mide con el mismo cuidado que lo que detecta.',
  ],
  'watch.formingNotNamed': ['Forming, not yet named', 'Formándose, aún sin identificar'],
  'watch.nothingForming': ['Nothing is forming at this interval.', 'No se está formando nada en este intervalo.'],
  'watch.beganAt': ['began at interval', 'empezó en el intervalo'],
  'watch.namedAt': ['named at', 'identificado en'],
  'receipt.emptyTitle': ['Certified-decision receipt', 'Recibo de decisión certificada'],
  'receipt.empty': [
    'A receipt is written when — and only when — the engine names an element. Until then there is nothing to certify, and the panel stays empty rather than filling with a guess.',
    'Se escribe un recibo cuando —y solo cuando— el motor identifica un elemento. Hasta entonces no hay nada que certificar, y el panel permanece vacío en lugar de llenarse con una suposición.',
  ],

  // ----- the recommended-action list -----
  'action.actOnElement': ['Act on the named element', 'Actuar sobre el elemento identificado'],
  'action.openTicket': ['Open a field ticket', 'Abrir un parte de campo'],
  'action.openTicket.sub': [
    'Pre-filled with the element, its layer, and the receipt',
    'Precargado con el elemento, su capa y el recibo',
  ],
  'action.preWarn': ['Pre-warn Customer Care', 'Avisar a Atención al Cliente'],
  'action.preWarn.sub': ['Suppress the inbound wave from', 'Contener la oleada de llamadas de'],
  'action.shareNoc': ['Share the receipt with the NOC', 'Compartir el recibo con el NOC'],
  'action.shareNoc.sub': [
    'Route the structural evidence to the transport desk',
    'Enviar la evidencia estructural a la mesa de transporte',
  ],
  'receipt.none': ['This verdict carried no receipt.', 'Este veredicto no traía recibo.'],

  // ----- management and map tabs -----
  'map.legend.baseline': ['at baseline', 'en la línea base'],
  'map.noVerdict': [
    'was ever named here. This region stayed at baseline for the whole run.',
    'se identificó aquí. Esta región permaneció en la línea base durante toda la ejecución.',
  ],
  'map.legend.forming': ['shape forming, not yet named', 'firma formándose, aún sin identificar'],


  // ----- management view -----
  'mgmt.pageTitle': ['Structural Intelligence — run scorecard', 'Inteligencia Estructural — marcador de la ejecución'],
  'mgmt.seed': ['seed', 'semilla'],
  'mgmt.computedIn': ['computed in', 'calculado en'],
  'mgmt.againstTruth': [
    'measured against ground truth the engine never sees.',
    'medido frente a una verdad de referencia que el motor nunca ve.',
  ],
  'mgmt.faultsDetected': ['Faults detected', 'Fallos detectados'],
  'mgmt.faultsDetected.d': ['every injected fault, named', 'todos los fallos inyectados, identificados'],
  'mgmt.meanLead': ['Mean lead time', 'Antelación media'],
  'mgmt.meanLead.d': ['before the fault would surface', 'antes de que el fallo aflorara'],
  'mgmt.localization': ['Localization', 'Localización'],
  'mgmt.localization.d': ['the right element, by name', 'el elemento correcto, por su nombre'],
  'mgmt.falsePositives': ['False positives', 'Falsos positivos'],
  'mgmt.spuriousOf': ['spurious of', 'espurios de'],
  'mgmt.quietIntervals': ['quiet intervals', 'intervalos en calma'],
  'mgmt.decoysHeld': ['Decoys held', 'Señuelos contenidos'],
  'mgmt.decoysHeld.d': ['benign spikes that did not fire', 'picos benignos que no dispararon'],
  'mgmt.selfTest': ['Self-test', 'Autoprueba'],
  'mgmt.selfTest.d': ['detected, attributed, box swap avoided', 'detectado, atribuido, sustitución evitada'],
  'mgmt.col.useCase': ['Use case', 'Caso de uso'],
  'mgmt.col.element': ['Element named', 'Elemento identificado'],
  'mgmt.col.detected': ['Detected', 'Detectado'],
  'mgmt.col.lead': ['Lead', 'Antelación'],
  'mgmt.col.localization': ['Localization', 'Localización'],
  'mgmt.col.layer': ['Layer', 'Capa'],
  'mgmt.col.boxSwap': ['Box swap', 'Sustitución STB'],
  'mgmt.decoysFired': ['Decoys fired', 'Señuelos disparados'],
  'mgmt.abstentions': ['Abstentions', 'Abstenciones'],
  'mgmt.abstention.some': [
    'Where the evidence would not resolve to a layer, the engine declined to name one. An abstention is a feature: it is the boundary of its own competence, stated out loud.',
    'Cuando la evidencia no permitía atribuir una capa, el motor se abstuvo de nombrarla. La abstención es una virtud: es el límite de su propia competencia, dicho en voz alta.',
  ],
  'mgmt.abstention.none': [
    'The engine resolved every disturbance it saw in this run.',
    'El motor resolvió todas las perturbaciones que vio en esta ejecución.',
  ],

  // ----- map view -----
  'map.regions': ['Regions in this run', 'Regiones de esta ejecución'],
  'map.verdictsHere': ['Verdicts here', 'Veredictos aquí'],
  'map.networkWeight': ['Network weight', 'Peso en la red'],

  // ----- live deck -----
  'live.watching': [
    'Watching the network live — faults appear the moment the engine names them',
    'Vigilando la red en directo: los fallos aparecen en cuanto el motor los identifica',
  ],

  // ----- states -----
  'state.startingTiny': ['Running the tiny network', 'Ejecutando la red reducida'],
  'state.startingFull': ['Running the full six-region network', 'Ejecutando la red completa de seis regiones'],
  'state.startingBody': [
    'Building the service graph, injecting the faults and the decoys, and letting the engine watch the four-field stream.',
    'Construyendo el grafo de servicio, inyectando los fallos y los señuelos, y dejando que el motor vigile el flujo de cuatro campos.',
  ],
  'state.failed': ['The run did not start', 'La ejecución no ha arrancado'],
  'state.failed.generic': ['Something went wrong.', 'Algo ha salido mal.'],
  'state.failed.needsApi': ['The console needs the API. Start it with', 'La consola necesita la API. Arráncala con'],
  'state.retry': ['Try again', 'Reintentar'],
} as const

export type StringKey = keyof typeof STRINGS

/** A translator bound to one language. */
export type T = (key: StringKey) => string

export function translator(lang: Lang): T {
  const index = lang === 'es' ? 1 : 0
  return (key) => STRINGS[key][index] ?? STRINGS[key][0]
}

/**
 * The layer and shape of a verdict, as words.
 *
 * These read off the engine's own codes, so the label can change language while the
 * value it names cannot. `format.ts` keeps the colours; the wording lives here.
 */
export function layerLabelOf(layer: string | null, t: T): string {
  if (!layer) return t('layerLabel.unresolved')
  const key = `layerLabel.${layer}` as StringKey
  return key in STRINGS ? t(key) : layer
}

export function shapeLabelOf(shape: string, t: T): string {
  const key = `shapeLabel.${shape}` as StringKey
  return key in STRINGS ? t(key) : shape
}
