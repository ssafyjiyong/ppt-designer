import json
import os
import uuid

import boto3

from shared.ddb_client import put_job

BUCKET = os.environ["BUCKET"]
_s3 = boto3.client("s3")

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
            "ContentType": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        },
        ExpiresIn=900,
    )
    put_job(job_id, source_key)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", **CORS},
        "body": json.dumps({"job_id": job_id, "upload_url": upload_url}),
    }
