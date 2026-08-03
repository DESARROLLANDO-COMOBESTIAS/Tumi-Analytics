"""Extract de Open-Meteo: clima actual por ciudad → Bronze."""

import datetime as dt
import re
from datetime import date

import httpx

from etl import s3
from etl.config import BRONZE_BUCKET, SOURCE_OPEN_METEO
from etl.logging import setup_logging

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CURRENT_PARAMS = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"

logger = setup_logging(__name__)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def fetch_weather(latitude: float, longitude: float, *, timeout: float = 30.0) -> dict:
    with httpx.Client(timeout=timeout) as client:
        response = client.get(
            OPEN_METEO_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": CURRENT_PARAMS,
                "timezone": "auto",
            },
        )
        response.raise_for_status()
        return response.json()


def extract(day: date, cities, client, *, force: bool = False) -> list[str]:
    """Extrae clima por ciudad y guarda el JSON original en Bronze."""
    keys = []
    for city in cities:
        try:
            raw = fetch_weather(city.latitude, city.longitude)
        except httpx.HTTPError as error:
            logger.warning("open_meteo_fetch_failed city=%s error=%s", city.name, error)
            continue
        envelope = {
            "_meta": {
                "source": SOURCE_OPEN_METEO,
                "city": city.name,
                "fetched_at": dt.datetime.now(dt.UTC).isoformat(),
            },
            "payload": raw,
        }
        key = f"open_meteo/{day.isoformat()}/{slugify(city.name)}.json"
        s3.put_json(client, BRONZE_BUCKET, key, envelope)
        keys.append(key)
    return keys


def handler(event, context) -> dict:
    day = date.fromisoformat(event.get("date") or dt.date.today().isoformat())
    from etl.cities import get_cities

    client = s3.get_client()
    keys = extract(day, get_cities(), client)
    logger.info("open_meteo_extract_completed date=%s files=%d", day.isoformat(), len(keys))
    return {"status": "ok", "date": day.isoformat(), "files": len(keys)}
