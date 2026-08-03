"""Acceso a S3 (LocalStack en local, AWS en producción)."""

import json
from collections.abc import Iterable

import boto3

from etl.config import AWS_ENDPOINT_URL, AWS_REGION


def get_client():
    kwargs = {"region_name": AWS_REGION}
    if AWS_ENDPOINT_URL:
        kwargs.update(
            endpoint_url=AWS_ENDPOINT_URL,
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
    return boto3.client("s3", **kwargs)


def put_json(client, bucket: str, key: str, obj: dict) -> None:
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(obj, ensure_ascii=False).encode("utf-8"),
    )


def put_jsonl(client, bucket: str, key: str, records: Iterable[dict]) -> None:
    body = "\n".join(
        json.dumps(rec, ensure_ascii=False) for rec in records
    ).encode("utf-8")
    client.put_object(Bucket=bucket, Key=key, Body=body)


def get_json(client, bucket: str, key: str) -> dict:
    response = client.get_object(Bucket=bucket, Key=key)
    return json.loads(response["Body"].read().decode("utf-8"))


def object_exists(client, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except client.exceptions.ClientError:
        return False
