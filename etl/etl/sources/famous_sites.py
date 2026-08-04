"""Catálogo curado de sitios turísticos famosos que quedan FUERA del
bounding box de su ciudad (Machu Picchu, volcanes, lagunas, cañones...).

Cada sitio se consulta con su propio bounding box y sus POIs se atribuyen
a la ciudad de ``city`` (una capital del Dataset Perú) para su conteo diario.
"""

import datetime as dt
import time

from etl import s3
from etl.config import BRONZE_BUCKET
from etl.logging import setup_logging
from etl.sources.overpass import (
    RATE_LIMIT_SECONDS,
    fetch_bbox,
    slugify,
)

logger = setup_logging(__name__)

FAMOUS_SITES: list[dict] = [
    {
        "name": "Machu Picchu",
        "city": "Cusco",
        "latitude": -13.1631,
        "longitude": -72.5450,
        "radius_deg": 0.02,
    },
    {
        "name": "Montaña Vinicunca",
        "city": "Cusco",
        "latitude": -13.8695,
        "longitude": -71.3030,
        "radius_deg": 0.02,
    },
    {
        "name": "Cañón del Colca",
        "city": "Arequipa",
        "points": [
            # Chivay: núcleo turístico (hoteles, restaurantes, info).
            {"latitude": -15.6367, "longitude": -71.6006, "radius_deg": 0.025},
            # Mirador Cruz del Cóndor: el atractivo del cañón.
            {"latitude": -15.6111, "longitude": -71.9064, "radius_deg": 0.025},
        ],
    },
    {
        "name": "Volcán Misti",
        "city": "Arequipa",
        "latitude": -16.2942,
        "longitude": -71.4095,
        "radius_deg": 0.02,
    },
    {
        "name": "Lago Titicaca",
        "city": "Puno",
        "points": [
            # Isla Taquile: hospedajes y restaurantes (fuera del bbox de Puno).
            {"latitude": -15.7658, "longitude": -69.6860, "radius_deg": 0.03},
            # Isla Amantani: marina y hospedajes.
            {"latitude": -15.6689, "longitude": -69.7046, "radius_deg": 0.03},
        ],
    },
    {
        "name": "Huacachina",
        "city": "Ica",
        "latitude": -14.0873,
        "longitude": -75.7633,
        "radius_deg": 0.02,
    },
    {
        "name": "Laguna 69",
        "city": "Huaraz",
        "latitude": -8.9769,
        "longitude": -77.6131,
        "radius_deg": 0.02,
    },
    {
        "name": "Kuélap",
        "city": "Chachapoyas",
        "latitude": -6.4180,
        "longitude": -77.9230,
        "radius_deg": 0.02,
    },
    {
        "name": "Caral",
        "city": "Lima",
        "latitude": -10.8919,
        "longitude": -77.5198,
        "radius_deg": 0.02,
    },
    {
        "name": "Líneas de Nazca",
        "city": "Ica",
        "latitude": -14.7191,
        "longitude": -75.1671,
        "radius_deg": 0.03,
    },
    {
        "name": "Chavín de Huántar",
        "city": "Huaraz",
        "latitude": -9.5889,
        "longitude": -77.1785,
        "radius_deg": 0.02,
    },
    {
        "name": "Chan Chan",
        "city": "Trujillo",
        "latitude": -8.1110,
        "longitude": -79.0745,
        "radius_deg": 0.02,
    },
    {
        "name": "Reserva de Paracas",
        "city": "Ica",
        "latitude": -13.8318,
        "longitude": -76.2510,
        "radius_deg": 0.03,
    },
]


def site_points(site: dict) -> list[dict]:
    """Puntos de consulta de un sitio (uno o varios bboxes por sitio)."""
    if "points" in site:
        return site["points"]
    return [
        {
            "latitude": site["latitude"],
            "longitude": site["longitude"],
            "radius_deg": site.get("radius_deg", 0.02),
        }
    ]


def fetch_site(
    site: dict,
    client,
    *,
    refresh: bool = False,
    day: dt.date | None = None,
) -> tuple[dict, str, str]:
    """Trae los POIs de un sitio famoso; usa caché S3 salvo ``refresh``.

    Un sitio puede definir varios puntos (bboxes) — p. ej. un cañón con su
    núcleo turístico y su mirador — y se fusionan sin duplicados.
    """
    day = day or dt.date.today()
    slug = slugify(site["name"])
    merged: dict[tuple[str, int], dict] = {}
    keys: list[str] = []
    all_cached = True
    for index, point in enumerate(site_points(site)):
        lat = float(point["latitude"])
        lon = float(point["longitude"])
        radius = float(point.get("radius_deg", 0.02))
        bbox = (lat - radius, lon - radius, lat + radius, lon + radius)
        key = f"overpass/famous/{day.isoformat()}/{slug}_p{index}.json"

        if not refresh and s3.object_exists(client, BRONZE_BUCKET, key):
            envelope = s3.get_json(client, BRONZE_BUCKET, key)
            payload = envelope["payload"]
            source = "cache"
        else:
            time.sleep(RATE_LIMIT_SECONDS)
            payload = fetch_bbox(bbox)
            envelope = {
                "_meta": {
                    "source": "overpass",
                    "site": site["name"],
                    "point": index,
                    "bbox": list(bbox),
                    "fetched_at": dt.datetime.now(dt.UTC).isoformat(),
                },
                "payload": payload,
            }
            s3.put_json(client, BRONZE_BUCKET, key, envelope)
            source = "extract"
            all_cached = False
        keys.append(key)
        logger.info(
            "overpass_extracted site=%s point=%d source=%s elements=%d",
            site["name"], index, source, len(payload.get("elements", [])),
        )
        for element in payload.get("elements", []):
            merged[(element.get("type", ""), element.get("id", 0))] = element

    source = "cache" if all_cached else "extract"
    return {"elements": list(merged.values())}, ",".join(keys), source


def handler(event, context) -> dict:
    site_name = event["site"]
    site = next(s for s in FAMOUS_SITES if s["name"] == site_name)
    client = s3.get_client()
    payload, key, source = fetch_site(
        site, client, refresh=event.get("refresh", False)
    )
    return {
        "status": "ok",
        "site": site["name"],
        "city": site["city"],
        "source": source,
        "key": key,
        "elements": len(payload.get("elements", [])),
    }
