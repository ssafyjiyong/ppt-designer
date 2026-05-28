import os
import time
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

TABLE_NAME = os.environ["JOBS_TABLE"]
_ddb = boto3.resource("dynamodb")
_table = _ddb.Table(TABLE_NAME)


def _to_ddb(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, list):
        return [_to_ddb(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_ddb(v) for k, v in value.items()}
    return value


def _from_ddb(value):
    if isinstance(value, Decimal):
        return float(value) if value % 1 else int(value)
    if isinstance(value, list):
        return [_from_ddb(v) for v in value]
    if isinstance(value, dict):
        return {k: _from_ddb(v) for k, v in value.items()}
    return value


def put_job(job_id: str, source_key: str):
    _table.put_item(
        Item={
            "pk": f"JOB#{job_id}",
            "sk": "META",
            "job_id": job_id,
            "source_key": source_key,
            "status": "created",
            "created_at": int(time.time()),
        }
    )


def update_job_status(job_id: str, status: str, **extra):
    expr = "SET #s = :s, updated_at = :t"
    values = {":s": status, ":t": int(time.time())}
    names = {"#s": "status"}
    for i, (k, v) in enumerate(extra.items()):
        expr += f", #{i} = :v{i}"
        names[f"#{i}"] = k
        values[f":v{i}"] = _to_ddb(v)
    _table.update_item(
        Key={"pk": f"JOB#{job_id}", "sk": "META"},
        UpdateExpression=expr,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )


def get_job(job_id: str):
    res = _table.get_item(Key={"pk": f"JOB#{job_id}", "sk": "META"})
    item = res.get("Item")
    return _from_ddb(item) if item else None


def put_slide_draft(job_id: str, index: int, draft_text: str):
    _table.put_item(
        Item={
            "pk": f"JOB#{job_id}",
            "sk": f"SLIDE#{index:03d}",
            "index": index,
            "draft_text": draft_text,
        }
    )


def put_slide_spec(job_id: str, index: int, spec: dict):
    _table.update_item(
        Key={"pk": f"JOB#{job_id}", "sk": f"SLIDE#{index:03d}"},
        UpdateExpression="SET spec = :s, designed_at = :t",
        ExpressionAttributeValues={":s": _to_ddb(spec), ":t": int(time.time())},
    )


def get_slide(job_id: str, index: int):
    res = _table.get_item(Key={"pk": f"JOB#{job_id}", "sk": f"SLIDE#{index:03d}"})
    item = res.get("Item")
    return _from_ddb(item) if item else None


def list_slides(job_id: str):
    res = _table.query(
        KeyConditionExpression=Key("pk").eq(f"JOB#{job_id}") & Key("sk").begins_with("SLIDE#")
    )
    return [_from_ddb(it) for it in res.get("Items", [])]
