import json
import os

import boto3

from shared.ddb_client import get_job, update_job_status

STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]
_sf = boto3.client("stepfunctions")

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def handler(event, context):
    job_id = event["pathParameters"]["job_id"]
    job = get_job(job_id)
    if not job:
        return _resp(404, {"error": "job not found"})

    update_job_status(job_id, "processing")
    _sf.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=f"job-{job_id}",
        input=json.dumps({"job_id": job_id, "source_key": job["source_key"]}),
    )
    return _resp(202, {"job_id": job_id, "status": "processing"})


def _resp(code: int, body: dict):
    return {"statusCode": code, "headers": {"Content-Type": "application/json", **CORS}, "body": json.dumps(body)}
