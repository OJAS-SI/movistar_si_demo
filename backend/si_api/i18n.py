"""
Spanish, and choosing between languages.

WHY SPANISH LIVES HERE AND NOT IN si_core

Which language an operator reads is a property of the request, not of the network. The
domain decides what is true and hands over a Msg; this layer decides which words the
caller gets, exactly as it already decides which JSON shape they get. si_core keeps the
canonical English because the text console and the HTML export have to render with no
API in sight - but nothing beyond English belongs in the domain.

TERMINOLOGY

Equipment and protocol names stay as an operations team writes them: OLT, STB, FEC,
SNR, WAN, CDN, set-top box, gateway, encoder, core. The prose around them is Spanish.
Translating the acronyms would read as unnatural to the engineers this console is for,
and would break the correspondence with the entity ids on the same screen.

A run's numbers never pass through here. Only its sentences do.
"""

from __future__ import annotations

from typing import Dict, Mapping

from si_core.messages import CATALOGUE_EN

DEFAULT_LANG = "en"
SUPPORTED_LANGS = ("en", "es")


CATALOGUE_ES: Dict[str, str] = {
    # ----- what the engine recommends -----
    "action.inspect_access_node":
        "inspeccionar el nodo de acceso y su agregación antes de que escalen las "
        "reclamaciones",
    "action.contact_customer_gateway":
        "contacto proactivo con el cliente y reconfiguración del gateway, sin "
        "desplazamiento de técnico",
    "action.investigate_core_route":
        "investigar la ruta de transporte de core que da servicio a los hogares afectados",
    "action.investigate_content_source":
        "investigar la fuente de contenido y su ruta de entrega",
    "action.watch_and_confirm":
        "puede estar formándose un clúster en este nodo de acceso, vigilar y confirmar",
    "action.escalate_to_human":
        "evidencia insuficiente o ambigua, escalar a revisión humana",
    "action.swap_set_top_box":
        "sustituir el set-top box",

    # ----- the operator headline -----
    "headline.cluster":
        "Nodo de acceso {entity} ({place}) degradándose: {n} hogares con congelaciones "
        "y resintonizaciones en aumento durante los últimos ~{minutes} min, firma de "
        "clúster de acceso local. Recomendación: {action}.",
    "headline.single":
        "Hogar {entity} ({place}) degradándose de forma aislada: congelaciones en "
        "aumento con conectividad doméstica débil durante los últimos ~{minutes} min, "
        "los hogares vecinos del nodo de acceso están sanos, firma de gateway doméstico "
        "aislado. Recomendación: {action}.",
    "headline.path":
        "Ruta de core {entity} degradándose: {n} hogares repartidos en {n_access} nodos "
        "de acceso afectados conjuntamente durante los últimos ~{minutes} min, firma de "
        "transporte de core compartido. Recomendación: {action}.",
    "headline.source":
        "Fuente de contenido {entity} ({channel}) degradándose: {n} hogares repartidos "
        "en {n_access} nodos de acceso que la consumen, afectados durante los últimos "
        "~{minutes} min, firma de fuente de contenido compartida. Recomendación: {action}.",
    "headline.abstention":
        "Límite de competencia: se está formando una perturbación pero la evidencia "
        "todavía no permite atribuirla a una capa. {action_cap}.",
    "headline.all_clear":
        "Todo correcto: ningún fallo en formación en la red monitorizada.",

    # ----- the same headlines as a title -----
    "headline.short.cluster": "Nodo de acceso {entity} degradándose",
    "headline.short.single": "Hogar {entity} en declive",
    "headline.short.path": "Ruta de core {entity} degradándose",
    "headline.short.source": "Fuente de contenido {entity} degradándose",
    "headline.short.abstention": "Límite de competencia",
    "headline.short.all_clear": "Todo correcto",

    # ----- the Structural Health Index bands -----
    "band.degraded_household": "degradado para el hogar",
    "band.critical_element": "crítico para el elemento afectado",
    "band.degraded_element": "degradado para el elemento afectado",
    "band.watch": "en observación",
    "band.healthy": "sano",

    "band.short.degraded_household": "Degradado",
    "band.short.critical_element": "Crítico",
    "band.short.degraded_element": "Degradado",
    "band.short.watch": "En observación",
    "band.short.healthy": "Sano",

    # ----- the certified-decision receipt -----
    "receipt.claim.cluster":
        "Nodo de acceso {entity} degradándose: {n} hogares por detrás con deterioro "
        "creciente",
    "receipt.claim.single":
        "Hogar {entity} degradándose de forma aislada; los hogares vecinos de su nodo "
        "de acceso están sanos",
    "receipt.claim.path":
        "Ruta de core {entity} degradándose: hogares de varios nodos de acceso "
        "afectados conjuntamente",
    "receipt.claim.source":
        "Fuente de contenido {entity} degradándose: hogares sin relación entre sí "
        "afectados conjuntamente",
    "receipt.claim.abstain":
        "Se está formando una perturbación pero la evidencia todavía no permite "
        "atribuirla a una capa",

    "receipt.check.cluster":
        "los hogares afectados comparten un mismo nodo de acceso y sus demás "
        "subsistemas están dentro de la línea base, lo que resulta incompatible con un "
        "fallo de contenido o de core",
    "receipt.check.single":
        "solo este hogar está afectado mientras que los vecinos de su nodo permanecen "
        "en la línea base, lo que resulta incompatible con un fallo de red compartido",
    "receipt.check.path":
        "los hogares afectados abarcan varios nodos de acceso pero comparten una misma "
        "ruta de core, lo que resulta incompatible con un fallo de nodo único o de "
        "contenido",
    "receipt.check.source":
        "los hogares afectados abarcan muchos nodos de acceso pero comparten una misma "
        "fuente de contenido, lo que resulta incompatible con un fallo de nodo de acceso",
    "receipt.check.abstain":
        "la firma estructural todavía no es lo bastante fuerte ni nítida para atribuirla",

    "receipt.support.elevated_sustained":
        "{n} hogares elevados y sostenidos por encima del umbral de permanencia",
    "receipt.support.elevated_sustained.one":
        "1 hogar elevado y sostenido por encima del umbral de permanencia",
    "receipt.support.mean_departure":
        "desviación media de {sigma} desviaciones típicas por encima de la línea base "
        "aprendida",
    "receipt.support.behind_node":
        "{n_behind} de {n} hogares elevados cuelgan de {dst} según el mapa de red",
    "receipt.support.behind_node.one":
        "{n_behind} de 1 hogar elevado cuelga de {dst} según el mapa de red",
    "receipt.support.elevated_near":
        "{n} hogares elevados cerca de {dst}",
    "receipt.support.elevated_near.one":
        "1 hogar elevado cerca de {dst}",
    "receipt.support.convergence_weak":
        "convergencia débil o ambigua; confianza por debajo del umbral de actuación",

    # ----- corroboration joined from enrichment (context, never the basis) -----
    "corrob.access_node":
        "utilización de puertos del nodo de acceso {util:.0%}, errores FEC {fec} "
        "(contexto corroborativo)",
    "corrob.home":
        "SNR del Wi-Fi doméstico {snr} dB, pérdida de paquetes WAN {loss}% "
        "(contexto corroborativo)",
    "corrob.content":
        "fallos de segmento de contenido {segments}, fotogramas descartados por el "
        "encoder {frames} (contexto corroborativo)",
    "corrob.core":
        "carga del transporte de core {load:.0%}, latencia de ruta {latency} ms "
        "(contexto corroborativo)",
    "corrob.example_home":
        "hogar de ejemplo {home}, congelación de {freeze}s en este intervalo",

    # ----- provenance -----
    "provenance.four_field_only":
        "solo el flujo de magnitud de cuatro campos; líneas base aprendidas del histórico",
    "provenance.competence_boundary":
        "límite de competencia alcanzado; se defiere a revisión humana",
    "provenance.derived":
        "derivado del flujo de magnitud de cuatro campos entre los intervalos {start} y "
        "{end}; {note}{signature}",
    "provenance.signature_spans":
        "; la firma abarca {n} hogares (p. ej., {sample})",
    "provenance.signature_spans.one":
        "; la firma abarca 1 hogar ({sample})",

    # ----- the console frame -----
    "console.subtitle":
        "con tecnología de Inteligencia Estructural  |  demo sintética, sin datos de Telefónica",
    "console.config_summary":
        "{homes} hogares, {olts} nodos de acceso, {regions} regiones, {intervals} "
        "intervalos con cadencia de {cadence} min",

    # ----- what each use case is here to show -----
    "panel.title.uc1_network_node":
        "Un nodo de red degradándose (fallo de acceso gradual)",
    "panel.title.uc2_individual":
        "Un hogar concreto degradándose (aislado, los vecinos sanos)",
    "panel.title.uc3_invisible":
        "Un fallo invisible que sobrevive a la sustitución del set-top box",
    "panel.title.uc4_core_path":
        "Una ruta de transporte de core degradándose (un camino entre nodos de acceso)",
    "panel.title.uc5_content_source":
        "Una fuente de contenido degradándose (hogares sin relación, una sola fuente)",

    # ----- the layers, as words in a sentence -----
    "layer.home": "de hogar",
    "layer.access": "de acceso",
    "layer.core": "de core",
    "layer.content": "de contenido",
    "layer.unknown": "desconocida",

    # ----- the four beats -----
    "beat.stream": "Flujo",
    "beat.form": "Formación",
    "beat.predict": "Predicción",
    "beat.prescribe": "Prescripción",
    "beat.stream.text":
        "{homes} hogares de {regions} regiones emiten telemetría de cuatro campos; el "
        "motor aprende lo normal y vigila la estructura del grafo.",
    "beat.form.text.cluster":
        "Se forma un clúster en la capa {layer}: firma de clúster en {entity}.",
    "beat.form.text.single":
        "Se forma un hogar aislado en la capa {layer}: firma individual en {entity}.",
    "beat.form.text.path":
        "Se forma un camino en la capa {layer}: firma de camino en {entity}.",
    "beat.form.text.source":
        "Se forma una fuente en la capa {layer}: firma de fuente en {entity}.",
    "beat.form.text.none":
        "Se forma una firma en la capa {layer}, en {entity}.",
    "beat.predict.text.widening_horizon":
        "Se proyecta que se amplíe ({detail}); con la tendencia actual se extendería "
        "hacia el intervalo {horizon} si no se actúa.",
    "beat.predict.text.widening": "Se proyecta que se amplíe ({detail}).",
    "beat.predict.text.steady":
        "Se proyecta estable; el motor sigue vigilando por si cambia.",
    "beat.prescribe.text":
        "{action_cap}. Señalado {minutes} min antes de que el fallo aflorara; véase el "
        "recibo de decisión certificada.",
    "beat.prescribe.text.no_lead":
        "{action_cap}. Véase el recibo de decisión certificada.",

    # ----- the scorecard, rendered as plain text -----
    "scorecard.heading":
        "Marcador de la demo de Inteligencia Estructural (valores medidos, sin umbrales "
        "preestablecidos)",
    "scorecard.detected": "detectados: {n}/{total}",
    "scorecard.lead_time":
        "antelación de detección: {intervals} intervalos ({minutes}) antes de que el "
        "fallo aflorara",
    "scorecard.localization": "precisión de localización: {pct}",
    "scorecard.layer_attribution": "atribución de capa: {pct}",
    "scorecard.box_swap":
        "discriminación de sustitución de set-top box: {pct} (se habría evitado la "
        "sustitución)",
    "scorecard.action_correctness": "corrección de la acción: {pct}",
    "scorecard.note": "nota: {note}",
    "scorecard.false_positive_rate":
        "tasa de falsos positivos: {pct} ({spurious} espurios de {total} intervalos sin fallo)",
    "scorecard.decoys_fired": "señuelos que dispararon: {fired}/{total}",
    "score.note.not_detected": "no detectado",
    "score.note.detected":
        "detectado en el intervalo {interval}, identificado {entity} ({layer}/{shape}), "
        "{lead} intervalos de antelación respecto al afloramiento en {surfacing}",

    # ----- the forward projection -----
    "trajectory.widening": "convergencia ampliándose",
    "trajectory.steady": "convergencia estable",
}


CATALOGUES: Dict[str, Mapping[str, str]] = {
    "en": CATALOGUE_EN,
    "es": CATALOGUE_ES,
}


def normalise_lang(value: str | None) -> str:
    """The language the caller asked for, reduced to one this demo actually ships.

    Accepts what a browser sends as well as what the UI sends: "es", "es-ES",
    "es-ES,es;q=0.9,en;q=0.8". Anything unrecognised falls back to English rather than
    failing the request - a console in the wrong language is recoverable, a 400 in the
    middle of a demo is not.
    """
    if not value:
        return DEFAULT_LANG
    for part in value.split(","):
        tag = part.split(";")[0].strip().lower()
        if not tag:
            continue
        primary = tag.split("-")[0]
        if primary in CATALOGUES:
            return primary
    return DEFAULT_LANG


def catalogue_for(lang: str | None) -> Mapping[str, str]:
    return CATALOGUES[normalise_lang(lang)]
