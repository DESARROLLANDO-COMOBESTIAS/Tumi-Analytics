"""Crea los buckets del Data Lake (Bronze/Silver/Gold).

Por defecto apunta a LocalStack (http://localhost:4566); para AWS real
usa variables de entorno de credenciales estándar y omite AWS_ENDPOINT_URL.
"""

import os

import boto3

ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
BUCKETS = ["tumi-bronze", "tumi-silver", "tumi-gold"]


def provision() -> None:
    s3 = boto3.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name=REGION,
    )
    existing = {b["Name"] for b in s3.list_buckets().get("Buckets", [])}
    for bucket in BUCKETS:
        if bucket not in existing:
            s3.create_bucket(Bucket=bucket)
            print(f"creado: {bucket}")
        else:
            print(f"ya existe: {bucket}")


if __name__ == "__main__":
    provision()
