"""Transformaciones limpias y normalizadas (Bronze → Silver).

Funciones puras y unit-testeadas: sin I/O para poder probarlas aisladas.
"""


def transform_open_meteo(payload: dict, city_name: str) -> dict | None:
    """Convierte el JSON crudo de Open-Meteo en un registro Silver de clima.

    Devuelve ``None`` si el payload no trae datos útiles.
    """
    current = payload.get("current") or {}
    time = current.get("time")
    if not time:
        return None
    temperature = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    precipitation = current.get("precipitation")
    wind_speed = current.get("wind_speed_10m")
    return {
        "date": time[:10],
        "city": city_name,
        "temperature_c": round(float(temperature), 1) if temperature is not None else None,
        "humidity": round(float(humidity), 1) if humidity is not None else None,
        "precipitation_mm": round(float(precipitation), 1)
        if precipitation is not None
        else None,
        "wind_speed_kmh": round(float(wind_speed), 1)
        if wind_speed is not None
        else None,
    }


def transform_exchange_rate(payload: dict) -> float | None:
    """Extrae el tipo de cambio USD → PEN del JSON crudo de la API.

    Devuelve ``None`` si la respuesta no es exitosa o no trae la moneda.
    """
    if payload.get("result") and payload.get("result") != "success":
        return None
    pen = (payload.get("rates") or {}).get("PEN")
    if pen is None:
        return None
    return round(float(pen), 4)
