"""Orquestador del pipeline ETL (Bronze → Silver → PostgreSQL).

Uso (local):
    tumi-etl weather            # clima del día
    tumi-etl exchange           # tipo de cambio del día
    tumi-etl all                # ambas fuentes
    tumi-etl all --date 2026-08-03
    tumi-etl all --force        # ignora last_sync
"""

import argparse
from datetime import date

from etl import s3, state
from etl.cities import get_cities
from etl.config import (
    BRONZE_BUCKET,
    SILVER_BUCKET,
    SOURCE_EXCHANGE_RATE,
    SOURCE_OPEN_METEO,
)
from etl.load import load_exchange_rate, load_weather
from etl.logging import setup_logging
from etl.sources import exchange_rate, open_meteo
from etl.transform import transform_exchange_rate, transform_open_meteo

logger = setup_logging()


def _should_run(client, source: str, day: date, force: bool) -> bool:
    if force:
        return True
    last = state.get_last_sync(client, source)
    if last == day:
        logger.info("skip source=%s reason=already_synced date=%s", source, day.isoformat())
        return False
    return True


def run_weather(day: date, force: bool) -> int:
    client = s3.get_client()
    if not _should_run(client, SOURCE_OPEN_METEO, day, force):
        return 0
    cities = get_cities()
    if not cities:
        logger.warning("open_meteo_aborted reason=no_cities_seeded")
        return 1

    keys = open_meteo.extract(day, cities, client)
    if not keys:
        logger.warning("open_meteo_aborted reason=no_data_extracted")
        return 1

    records = []
    for key in keys:
        envelope = s3.get_json(client, BRONZE_BUCKET, key)
        record = transform_open_meteo(envelope["payload"], envelope["_meta"]["city"])
        if record is not None:
            records.append(record)

    silver_key = f"open_meteo/{day.isoformat()}/daily.jsonl"
    s3.put_jsonl(client, SILVER_BUCKET, silver_key, records)

    loaded = load_weather(day, records)
    state.set_last_sync(client, SOURCE_OPEN_METEO, day)
    logger.info(
        "open_meteo_completed date=%s extracted=%d loaded=%d silver=%s",
        day.isoformat(), len(keys), loaded, silver_key,
    )
    return 0


def run_exchange(day: date, force: bool) -> int:
    client = s3.get_client()
    if not _should_run(client, SOURCE_EXCHANGE_RATE, day, force):
        return 0

    key = exchange_rate.extract(day, client)
    if not key:
        logger.warning("exchange_rate_aborted reason=no_data_extracted")
        return 1

    envelope = s3.get_json(client, BRONZE_BUCKET, key)
    rate = transform_exchange_rate(envelope["payload"])
    if rate is None:
        logger.warning("exchange_rate_aborted reason=transform_rejected")
        return 1

    silver_key = f"exchange_rate/{day.isoformat()}/usd_pen.json"
    s3.put_json(client, SILVER_BUCKET, silver_key, {"date": day.isoformat(), "usd_pen": rate})

    loaded = load_exchange_rate(day, rate)
    state.set_last_sync(client, SOURCE_EXCHANGE_RATE, day)
    logger.info(
        "exchange_rate_completed date=%s usd_pen=%.4f cities=%d silver=%s",
        day.isoformat(), rate, loaded, silver_key,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tumi-etl", description="Pipeline ETL de Tumi Analytics")
    parser.add_argument("job", choices=["weather", "exchange", "all"])
    parser.add_argument("--date", type=date.fromisoformat, default=None, help="YYYY-MM-DD")
    parser.add_argument("--force", action="store_true", help="Ignora last_sync")
    args = parser.parse_args(argv)

    day = args.date or date.today()
    exit_code = 0
    if args.job in ("weather", "all"):
        exit_code = max(exit_code, run_weather(day, args.force))
    if args.job in ("exchange", "all"):
        exit_code = max(exit_code, run_exchange(day, args.force))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
