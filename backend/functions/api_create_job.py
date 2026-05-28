import json
import os
import uuid

import boto3
from botocore.client import Config

from shared.ddb_client import put_job

BUCKET = os.environ["BUCKET"]
_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")
_s3 = boto3.client(
    "s3",
    region_name=_REGION,
    endpoint_url=f"https://s3.{_REGION}.amazonaws.com",
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def handler(event, context):
    job_id = uuid.uuid4().hex[:12]
    source_key = f"uploads/{job_id}/source.pptx"
    upload_url = _s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": BUCKET,
            "Key": source_key,
        },
        ExpiresIn=900,
    )
    put_job(job_id, source_key)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", **CORS},
        "body": json.dumps({"job_id": job_id, "upload_url": upload_url}),
    }
