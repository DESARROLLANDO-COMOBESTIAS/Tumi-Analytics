"""Extract de POIs desde OpenStreetMap vía Overpass API.

Diseño robusto (no adivinar categorías):
- Se captura AMPLIO: todo lo etiquetado como turístico, histórico, de ocio
  (leisure), natural y los servicios que importan (restaurantes, hospitales,
  templos). Así nunca se pierde algo en silencio por una lista incompleta.
- Cada elemento se agrupa en categorías de negocio que crecen con datos reales
  (dim_poi_category). Un elemento puede sumar a varias categorías.
- El ruido conocido (árboles, canchas, piscinas, gimnasios...) se descarta.
- Lo que no entra en ninguna categoría conocida cae en "sin_clasificar" para
  revisarlo: si aparece mucho, es señal de que falta una categoría.

Límites de la API:
- Sin clave; respetar ~1 consulta cada 5 s y acotar el área (bounding box).
- El servidor público puede estar saturado: reintentos con espera y caché en S3.
"""

import datetime as dt
import re
import time

import httpx

from etl import s3
from etl.config import BRONZE_BUCKET
from etl.logging import setup_logging

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
MAX_ATTEMPTS = 4
RATE_LIMIT_SECONDS = 5.0

logger = setup_logging(__name__)

# Claves que capturamos de forma amplia. Todo elemento con una de estas claves
# se considera "candidato"; si no clasifica ni es ruido, va a sin_clasificar.
CAPTURED_KEYS = ("tourism", "historic", "leisure", "natural")

# Ruido conocido: etiquetas que OSM usa mucho pero no son atractivos turísticos.
NOISE_TAGS: frozenset[tuple[str, str]] = frozenset(
    {
        ("natural", "tree"),
        ("natural", "wood"),
        ("natural", "scrub"),
        ("natural", "grassland"),
        ("natural", "heath"),
        ("natural", "water"),
        ("natural", "sand"),
        ("natural", "bare_rock"),
        ("natural", "shingle"),
        ("leisure", "pitch"),
        ("leisure", "playground"),
        ("leisure", "sports_centre"),
        ("leisure", "swimming_pool"),
        ("leisure", "fitness_centre"),
        ("leisure", "fitness_station"),
        ("leisure", "track"),
        ("leisure", "stadium"),
        ("leisure", "sauna"),
        ("leisure", "amusement_arcade"),
        ("leisure", "miniature_golf"),
        ("leisure", "outdoor_seating"),
        ("leisure", "indoor_play"),
        ("leisure", "horse_riding"),
        ("leisure", "recreation_ground"),
        ("leisure", "dance"),
        ("leisure", "adult_gaming_centre"),
        ("leisure", "firepit"),
        ("leisure", "golf_course"),
        ("leisure", "common"),
        ("historic", "yes"),
        ("tourism", "yes"),
        ("leisure", "yes"),
        # Señales del censo de sin_clasificar: tumbas de cementerio y ocio menor.
        ("historic", "tomb"),
        ("leisure", "bleachers"),
        ("leisure", "dog_park"),
        ("leisure", "picnic_table"),
        ("leisure", "sports_hall"),
        ("leisure", "escape_game"),
        ("leisure", "bowling_alley"),
    }
)

# Categoría de negocio (código de dim_poi_category) -> etiquetas que la definen.
CATEGORY_TAGS: dict[str, list[tuple[str, str]]] = {
    "hoteles": [
        ("tourism", "hotel"),
        ("tourism", "hostel"),
        ("tourism", "guest_house"),
        ("tourism", "motel"),
        ("tourism", "apartment"),
        ("tourism", "chalet"),
        ("tourism", "camp_site"),
        ("tourism", "caravan_site"),
    ],
    "restaurantes": [
        ("amenity", "restaurant"),
        ("amenity", "fast_food"),
        ("amenity", "cafe"),
        ("amenity", "bar"),
    ],
    "museos": [("tourism", "museum")],
    "galerias": [("tourism", "gallery")],
    "arte_urbano": [("tourism", "artwork")],
    "parques": [("leisure", "park"), ("leisure", "garden")],
    "reservas": [("leisure", "nature_reserve")],
    "hospitales": [("amenity", "hospital")],
    "atracciones": [
        ("tourism", "attraction"),
        ("tourism", "zoo"),
        ("tourism", "aquarium"),
        ("tourism", "theme_park"),
        ("tourism", "picnic_site"),
    ],
    "arqueologicos": [("historic", "archaeological_site"), ("historic", "ruins")],
    "castillos": [("historic", "castle"), ("historic", "fort")],
    "murallas": [("historic", "citywalls"), ("historic", "city_gate")],
    "monumentos": [("historic", "monument"), ("historic", "memorial")],
    "iglesias": [
        ("amenity", "place_of_worship"),
        ("amenity", "monastery"),
        ("historic", "church"),
        ("historic", "chapel"),
        ("historic", "monastery"),
    ],
    "miradores": [("tourism", "viewpoint")],
    "playas": [("natural", "beach")],
    "montanas": [
        ("natural", "peak"),
        ("natural", "ridge"),
        ("natural", "cliff"),
        ("natural", "valley"),
        ("natural", "glacier"),
    ],
    "cuevas": [("natural", "cave_entrance")],
    "volcanes": [("natural", "volcano")],
    "aguas_termales": [("natural", "hot_spring"), ("natural", "spring"), ("natural", "geyser")],
    "informacion_turistica": [("tourism", "information")],
    "ermitas_cruces": [("historic", "wayside_shrine"), ("historic", "wayside_cross")],
    "marinas_resorts": [
        ("leisure", "marina"),
        ("leisure", "resort"),
        ("leisure", "water_park"),
    ],
}

UNCLASSIFIED = "sin_clasificar"

# Códigos de categorías en el orden natural de presentación.
ALL_CATEGORIES: list[str] = [*CATEGORY_TAGS, UNCLASSIFIED]

AMENITY_CAPTURE = (
    "restaurant|fast_food|cafe|bar|hospital|place_of_worship|monastery"
)

# Naturaleza con interés turístico. El resto (árboles, matorrales, ríos, ...)
# es ruido que no se consulta para mantener las respuestas pequeñas y rápidas.
NATURAL_CAPTURE = (
    "peak|volcano|waterfall|cave_entrance|hot_spring|spring|beach|ridge|"
    "cliff|valley|geyser|glacier|sinkhole"
)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def build_statements(bbox: tuple[float, float, float, float]) -> list[str]:
    """Consulta amplia por partes: turismo, histórico, ocio, naturaleza y servicios.

    Se consulta cada clave por separado (no una gran unión) porque el servidor
    público de Overpass da timeout con la unión grande; las consultas pequeñas
    son rápidas y estables.
    """
    south, west, north, east = bbox
    box = f"({south:.4f},{west:.4f},{north:.4f},{east:.4f})"
    return [
        f'[out:json][timeout:60];nwr["tourism"]{box};out center tags;',
        f'[out:json][timeout:60];nwr["historic"]{box};out center tags;',
        f'[out:json][timeout:60];nwr["leisure"]{box};out center tags;',
        f'[out:json][timeout:60];nwr["natural"~"^({NATURAL_CAPTURE})$"]{box};out center tags;',
        f'[out:json][timeout:60];nwr["amenity"~"^({AMENITY_CAPTURE})$"]{box};out center tags;',
    ]


def _fetch_statement(statement: str, *, timeout: float = 120.0) -> dict:
    """Consulta una parte del bbox con reintentos y failover entre servidores."""
    headers = {"User-Agent": "TumiAnalytics/0.1 (ETL) contact@tumi.local"}
    with httpx.Client(timeout=timeout, headers=headers) as client:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            for url in OVERPASS_URLS:
                try:
                    response = client.get(url, params={"data": statement})
                except httpx.HTTPError as exc:
                    logger.warning(
                        "overpass_retry attempt=%d/%d url=%s error=%s",
                        attempt, MAX_ATTEMPTS, url, exc.__class__.__name__,
                    )
                    continue
                if response.status_code == 200:
                    return response.json()
                logger.warning(
                    "overpass_retry attempt=%d/%d url=%s status=%d",
                    attempt, MAX_ATTEMPTS, url, response.status_code,
                )
            wait = RATE_LIMIT_SECONDS * (2 ** (attempt - 1))
            logger.warning("overpass_backoff wait=%.1fs", wait)
            time.sleep(wait)
    raise RuntimeError("Overpass sin respuesta tras reintentos")


def fetch_bbox(bbox: tuple[float, float, float, float], *, timeout: float = 120.0) -> dict:
    """Trae POIs de un bbox por partes y los une sin duplicados.

    Un elemento puede aparecer en varias consultas (ej. hotel con restaurante);
    se deduplica por (tipo, id).
    """
    merged: dict[tuple[str, int], dict] = {}
    for statement in build_statements(bbox):
        payload = _fetch_statement(statement, timeout=timeout)
        for element in payload.get("elements", []):
            merged[(element.get("type", ""), element.get("id", 0))] = element
    return {"elements": list(merged.values())}


def classify_element(tags: dict) -> list[str]:
    """Categorías de negocio de un elemento (puede ser varias o sin_clasificar)."""
    if not (any(key in tags for key in CAPTURED_KEYS) or "amenity" in tags):
        return []
    matched = [
        category
        for category, pairs in CATEGORY_TAGS.items()
        if any(tags.get(key) == value for key, value in pairs)
    ]
    if matched:
        return matched
    captured = [
        (key, tags[key])
        for key in (*CAPTURED_KEYS, "amenity")
        if key in tags
    ]
    if captured and all(pair in NOISE_TAGS for pair in captured):
        return []
    return [UNCLASSIFIED]


def classify_counts(elements: list[dict]) -> dict[str, int]:
    """Cuenta elementos por categoría de negocio (incluye sin_clasificar)."""
    counts = {category: 0 for category in ALL_CATEGORIES}
    for element in elements:
        for category in classify_element(element.get("tags") or {}):
            counts[category] += 1
    return counts


def _fetch_cached(
    name: str,
    latitude: float,
    longitude: float,
    client,
    *,
    prefix: str,
    radius_deg: float,
    refresh: bool,
    day: dt.date,
) -> tuple[dict, str, str]:
    bbox = (
        latitude - radius_deg,
        longitude - radius_deg,
        latitude + radius_deg,
        longitude + radius_deg,
    )
    key = f"{prefix}/{day.isoformat()}/{slugify(name)}.json"

    if not refresh and s3.object_exists(client, BRONZE_BUCKET, key):
        envelope = s3.get_json(client, BRONZE_BUCKET, key)
        logger.info("overpass_used_cache name=%s key=%s", name, key)
        return envelope["payload"], key, "cache"

    time.sleep(RATE_LIMIT_SECONDS)
    payload = fetch_bbox(bbox)
    envelope = {
        "_meta": {
            "source": "overpass",
            "name": name,
            "bbox": list(bbox),
            "fetched_at": dt.datetime.now(dt.UTC).isoformat(),
        },
        "payload": payload,
    }
    s3.put_json(client, BRONZE_BUCKET, key, envelope)
    logger.info(
        "overpass_extracted name=%s elements=%d", name, len(payload.get("elements", []))
    )
    return payload, key, "extract"


def spike_city(
    city_name: str,
    latitude: float,
    longitude: float,
    client,
    *,
    radius_deg: float = 0.06,
    refresh: bool = False,
    day: dt.date | None = None,
) -> tuple[dict, str, str]:
    """POIs de una ciudad por bounding box para el spike (usa caché S3)."""
    return _fetch_cached(
        city_name, latitude, longitude, client,
        prefix="overpass/spike", radius_deg=radius_deg,
        refresh=refresh, day=day or dt.date.today(),
    )


def poi_city(
    city_name: str,
    latitude: float,
    longitude: float,
    client,
    *,
    radius_deg: float = 0.06,
    refresh: bool = False,
    day: dt.date | None = None,
) -> tuple[dict, str, str]:
    """POIs de una ciudad para el ETL diario (usa caché S3)."""
    return _fetch_cached(
        city_name, latitude, longitude, client,
        prefix="overpass/poi", radius_deg=radius_deg,
        refresh=refresh, day=day or dt.date.today(),
    )


def handler(event, context) -> dict:
    city_name = event["city"]
    lat = float(event["latitude"])
    lon = float(event["longitude"])
    client = s3.get_client()
    payload, key, source = poi_city(
        city_name, lat, lon, client, refresh=event.get("refresh", False)
    )
    counts = classify_counts(payload.get("elements", []))
    return {"status": "ok", "city": city_name, "source": source, "key": key, "counts": counts}
