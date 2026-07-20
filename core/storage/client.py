from functools import lru_cache

import boto3
from botocore.config import Config as AWSConfig
from botocore.exceptions import ClientError

from core.log import Logger
from core.settings import Config

log = Logger(name='storage')


@lru_cache(maxsize=1)
def _client():
    """Lazy singleton so a missing/bad storage env var only breaks storage calls, not app boot."""
    return boto3.client(
        "s3",
        endpoint_url=Config.SUPABASE_STORAGE_URL,
        region_name=Config.SUPABASE_STORAGE_REGION,
        aws_access_key_id=Config.SUPABASE_STORAGE_ACCESS_ID,
        aws_secret_access_key=Config.SUPABASE_STORAGE_ACCESS_SECRET,
        config=AWSConfig(s3={"addressing_style": "path"}),
    )


def upload(bucket: str, key: str, filename: str) -> None:
    try:
        _client().upload_file(Bucket=bucket, Key=key, Filename=filename)
        log.fire.info(f'uploaded {filename} -> {key}')
    except ClientError as e:
        log.fire.error(f'{e}')
        raise


def download(bucket: str, key: str, filename: str) -> None:
    try:
        _client().download_file(Bucket=bucket, Key=key, Filename=filename)
        log.fire.info(f'downloaded {key} -> {filename}')
    except ClientError as e:
        log.fire.error(f'{e}')
        raise


def get_text(bucket: str, key: str) -> str:
    try:
        obj = _client().get_object(Bucket=bucket, Key=key)
        return obj['Body'].read().decode('utf-8')
    except ClientError as e:
        log.fire.error(f'{e}')
        raise


def put_text(bucket: str, key: str, content: str) -> None:
    try:
        _client().put_object(Bucket=bucket, Key=key, Body=content.encode('utf-8'))
    except ClientError as e:
        log.fire.error(f'{e}')
        raise


def exists(bucket: str, key: str) -> bool:
    try:
        _client().head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


def list_files(bucket: str, prefix: str = '') -> list[str]:
    keys: list[str] = []
    paginator = _client().get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        keys.extend(obj['Key'] for obj in page.get('Contents', []))
    return keys


def list_prefixes(bucket: str, prefix: str) -> list[str]:
    """Immediate 'subdirectories' under prefix (e.g. NPC slugs under a user's namespace)."""
    response = _client().list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter='/')
    return [cp['Prefix'] for cp in response.get('CommonPrefixes', [])]


def delete_prefix(bucket: str, prefix: str) -> None:
    keys = list_files(bucket, prefix)
    if not keys:
        return
    try:
        _client().delete_objects(Bucket=bucket, Delete={'Objects': [{'Key': k} for k in keys]})
        log.fire.info(f'deleted {len(keys)} objects under {prefix}')
    except ClientError as e:
        log.fire.error(f'{e}')
        raise
