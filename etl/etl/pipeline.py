"""Orquestador del pipeline ETL (Bronze → Silver → PostgreSQL).

Uso (local):
    tumi-etl weather            # clima del día
    tumi-etl exchange           # tipo de cambio del día
    tumi-etl all                # clima + tipo de cambio
    tumi-etl poi                # conteos de POIs (25 ciudades + sitios famosos)
    tumi-etl poi --cities Cusco Arequipa
    tumi-etl poi --force        # ignora last_sync
    tumi-etl poi --refresh      # ignora la caché S3
    tumi-etl all --date 2026-08-03
    tumi-etl spike              # valida POIs (Cusco y Arequipa)
    tumi-etl spike --cities Lima Cusco
    tumi-etl spike --refresh    # ignora la caché S3
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
    SOURCE_POI,
)
from etl.load import load_exchange_rate, load_poi, load_weather
from etl.logging import setup_logging
from etl.sources import exchange_rate, famous_sites, open_meteo, overpass
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


def run_spike(cities: list[str], refresh: bool) -> int:
    client = s3.get_client()
    city_by_name = {city.name: city for city in get_cities()}
    per_city: dict[str, tuple[str, dict[str, int]]] = {}
    for name in cities:
        city = city_by_name.get(name)
        if city is None:
            logger.warning("spike_skipped city=%s reason=not_in_catalog", name)
            continue
        payload, key, source = overpass.spike_city(
            city.name, city.latitude, city.longitude, client, refresh=refresh
        )
        counts = overpass.classify_counts(payload.get("elements", []))
        per_city[name] = (source, counts)
        logger.info("spike_city_completed city=%s source=%s counts=%s", name, source, counts)

    if not per_city:
        return 1

    rows = [(name, source, counts) for name, (source, counts) in per_city.items()]
    _print_poi_table("SPIKE POIs (Overpass)", rows)
    return 0


def run_poi(
    day: date,
    cities: list[str] | None,
    force: bool,
    refresh: bool,
) -> int:
    client = s3.get_client()
    if not _should_run(client, SOURCE_POI, day, force):
        return 0

    city_by_name = {city.name: city for city in get_cities()}
    targets = cities if cities else [city.name for city in city_by_name.values()]

    per_city: dict[str, dict[str, int]] = {}
    for name in targets:
        city = city_by_name.get(name)
        if city is None:
            logger.warning("poi_skipped city=%s reason=not_in_catalog", name)
            continue
        payload, key, source = overpass.poi_city(
            city.name, city.latitude, city.longitude, client,
            refresh=refresh, day=day,
        )
        counts = overpass.classify_counts(payload.get("elements", []))
        per_city[name] = counts
        logger.info(
            "poi_city_completed city=%s source=%s counts=%s", name, source, counts
        )

    for site in famous_sites.FAMOUS_SITES:
        payload, key, source = famous_sites.fetch_site(
            site, client, refresh=refresh, day=day
        )
        counts = overpass.classify_counts(payload.get("elements", []))
        city = city_by_name.get(site["city"])
        if city is None:
            logger.warning(
                "poi_site_skipped site=%s reason=city_not_in_catalog", site["name"]
            )
            continue
        bucket = per_city.setdefault(city.name, {c: 0 for c in overpass.ALL_CATEGORIES})
        for category, value in counts.items():
            bucket[category] = bucket.get(category, 0) + value
        logger.info(
            "poi_site_completed site=%s city=%s source=%s counts=%s",
            site["name"], city.name, source, counts,
        )

    if not per_city:
        return 1

    silver_key = f"poi/{day.isoformat()}/counts.jsonl"
    records = [
        {"date": day.isoformat(), "city": city_name, "category": code, "count": count}
        for city_name, counts in per_city.items()
        for code, count in counts.items()
        if count > 0
    ]
    s3.put_jsonl(client, SILVER_BUCKET, silver_key, records)

    loaded = load_poi(day, per_city)
    state.set_last_sync(client, SOURCE_POI, day)
    logger.info(
        "poi_completed date=%s cities=%d loaded=%d silver=%s",
        day.isoformat(), len(per_city), loaded, silver_key,
    )

    rows = [(name, "loaded", counts) for name, counts in per_city.items()]
    _print_poi_table("CONTEOS POIs (fact_poi_city)", rows)
    return 0


def _print_poi_table(title: str, rows: list[tuple[str, str, dict[str, int]]]) -> None:
    """Imprime conteos por ciudad mostrando solo columnas con datos."""
    if not rows:
        return
    categories = [
        category
        for category in overpass.ALL_CATEGORIES
        if any(counts.get(category, 0) > 0 for _, _, counts in rows)
    ]
    header = ["Ciudad", "Fuente", *categories]
    widths = [len(h) for h in header]
    lines = [
        [name, source, *[str(counts.get(cat, 0)) for cat in categories]]
        for name, source, counts in rows
    ]
    for line in lines:
        for i, cell in enumerate(line):
            widths[i] = max(widths[i], len(cell))
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(f"\n=== {title} ===")
    print(fmt.format(*header))
    print("  ".join("-" * w for w in widths))
    for line in lines:
        print(fmt.format(*line))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tumi-etl", description="Pipeline ETL de Tumi Analytics")
    parser.add_argument("job", choices=["weather", "exchange", "all", "spike", "poi"])
    parser.add_argument("--date", type=date.fromisoformat, default=None, help="YYYY-MM-DD")
    parser.add_argument("--force", action="store_true", help="Ignora last_sync")
    parser.add_argument(
        "--cities", nargs="+", default=None,
        help="Ciudades (spike: por defecto Cusco y Arequipa; poi: todas)",
    )
    parser.add_argument("--refresh", action="store_true", help="Ignora la caché S3")
    args = parser.parse_args(argv)

    if args.job == "spike":
        return run_spike(args.cities or ["Cusco", "Arequipa"], args.refresh)

    if args.job == "poi":
        return run_poi(args.date or date.today(), args.cities, args.force, args.refresh)

    day = args.date or date.today()
    exit_code = 0
    if args.job in ("weather", "all"):
        exit_code = max(exit_code, run_weather(day, args.force))
    if args.job in ("exchange", "all"):
        exit_code = max(exit_code, run_exchange(day, args.force))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
