"""Estado de sincronización (last_sync) por fuente, persistido en S3 Bronze."""

from datetime import date

from etl import s3
from etl.config import BRONZE_BUCKET

STATE_KEY = "state/last_sync.json"


def get_last_sync(client, source: str) -> date | None:
    if not s3.object_exists(client, BRONZE_BUCKET, STATE_KEY):
        return None
    data = s3.get_json(client, BRONZE_BUCKET, STATE_KEY)
    value = data.get(source)
    return date.fromisoformat(value) if value else None


def set_last_sync(client, source: str, day: date) -> None:
    data = {}
    if s3.object_exists(client, BRONZE_BUCKET, STATE_KEY):
        data = s3.get_json(client, BRONZE_BUCKET, STATE_KEY)
    data[source] = day.isoformat()
    s3.put_json(client, BRONZE_BUCKET, STATE_KEY, data)
