from etl.transform import transform_exchange_rate, transform_open_meteo


def _weather_payload(**overrides):
    current = {
        "time": "2026-08-03T10:00",
        "temperature_2m": 18.55,
        "relative_humidity_2m": 82.3,
        "precipitation": 0.25,
        "wind_speed_10m": 14.7,
    }
    current.update(overrides.get("current", {}))
    return {"current": current, **overrides.get("meta", {})}


class TestTransformOpenMeteo:
    def test_valido_redondea_y_extrae_fecha(self):
        record = transform_open_meteo(_weather_payload(), "Lima")
        assert record == {
            "date": "2026-08-03",
            "city": "Lima",
            "temperature_c": 18.6,
            "humidity": 82.3,
            "precipitation_mm": 0.2,
            "wind_speed_kmh": 14.7,
        }

    def test_sin_current_devuelve_none(self):
        assert transform_open_meteo({"current": {}}, "Lima") is None

    def test_sin_time_devuelve_none(self):
        payload = {"current": {"time": None, "temperature_2m": 20.0}}
        assert transform_open_meteo(payload, "Lima") is None

    def test_valores_nulos_se_mantienen_nulos(self):
        payload = {"current": {"time": "2026-08-03T10:00", "temperature_2m": None}}
        record = transform_open_meteo(payload, "Lima")
        assert record is not None
        assert record["temperature_c"] is None
        assert record["humidity"] is None


class TestTransformExchangeRate:
    def test_valido(self):
        payload = {"result": "success", "rates": {"USD": 1.0, "PEN": 3.7565}}
        assert transform_exchange_rate(payload) == 3.7565

    def test_sin_pen_devuelve_none(self):
        assert transform_exchange_rate({"result": "success", "rates": {"USD": 1.0}}) is None

    def test_result_no_exitoso_devuelve_none(self):
        payload = {"result": "error", "rates": {"PEN": 3.7}}
        assert transform_exchange_rate(payload) is None
