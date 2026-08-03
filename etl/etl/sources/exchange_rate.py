"""Extract de ExchangeRate: tipo de cambio USD → PEN → Bronze."""

import datetime as dt
from datetime import date

import httpx

from etl import s3
from etl.config import BRONZE_BUCKET, SOURCE_EXCHANGE_RATE
from etl.logging import setup_logging

EXCHANGE_RATE_URL = "https://open.er-api.com/v6/latest/USD"

logger = setup_logging(__name__)


def fetch_rates(*, timeout: float = 30.0) -> dict:
    with httpx.Client(timeout=timeout) as client:
        response = client.get(EXCHANGE_RATE_URL)
        response.raise_for_status()
        return response.json()


def extract(day: date, client, *, force: bool = False) -> str | None:
    """Trae el tipo de cambio y guarda el JSON original en Bronze."""
    try:
        raw = fetch_rates()
    except httpx.HTTPError as error:
        logger.warning("exchange_rate_fetch_failed error=%s", error)
        return None
    envelope = {
        "_meta": {
            "source": SOURCE_EXCHANGE_RATE,
            "fetched_at": dt.datetime.now(dt.UTC).isoformat(),
        },
        "payload": raw,
    }
    key = f"exchange_rate/{day.isoformat()}/usd_pen.json"
    s3.put_json(client, BRONZE_BUCKET, key, envelope)
    return key


def handler(event, context) -> dict:
    day = date.fromisoformat(event.get("date") or dt.date.today().isoformat())
    client = s3.get_client()
    key = extract(day, client)
    logger.info("exchange_rate_extract_completed date=%s key=%s", day.isoformat(), key)
    return {"status": "ok", "date": day.isoformat(), "key": key}
