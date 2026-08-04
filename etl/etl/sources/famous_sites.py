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
        "latitude": -15.6464,
        "longitude": -71.8933,
        "radius_deg": 0.03,
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
        "latitude": -15.8267,
        "longitude": -69.3238,
        "radius_deg": 0.05,
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


def fetch_site(
    site: dict,
    client,
    *,
    refresh: bool = False,
    day: dt.date | None = None,
) -> tuple[dict, str, str]:
    """Trae los POIs del bbox de un sitio famoso; usa caché S3 salvo ``refresh``."""
    day = day or dt.date.today()
    lat = float(site["latitude"])
    lon = float(site["longitude"])
    radius = float(site.get("radius_deg", 0.02))
    bbox = (lat - radius, lon - radius, lat + radius, lon + radius)
    key = f"overpass/famous/{day.isoformat()}/{slugify(site['name'])}.json"

    if not refresh and s3.object_exists(client, BRONZE_BUCKET, key):
        envelope = s3.get_json(client, BRONZE_BUCKET, key)
        logger.info("overpass_used_cache site=%s key=%s", site["name"], key)
        return envelope["payload"], key, "cache"

    time.sleep(RATE_LIMIT_SECONDS)
    payload = fetch_bbox(bbox)
    envelope = {
        "_meta": {
            "source": "overpass",
            "site": site["name"],
            "bbox": list(bbox),
            "fetched_at": dt.datetime.now(dt.UTC).isoformat(),
        },
        "payload": payload,
    }
    s3.put_json(client, BRONZE_BUCKET, key, envelope)
    logger.info(
        "overpass_extracted site=%s elements=%d", site["name"], len(payload.get("elements", []))
    )
    return payload, key, "extract"


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
