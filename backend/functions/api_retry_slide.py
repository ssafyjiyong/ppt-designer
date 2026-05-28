import json
import os

import boto3

from shared.ddb_client import get_job, get_slide, update_job_status

STATE_MACHINE_ARN = os.environ["RETRY_STATE_MACHINE_ARN"]
_sf = boto3.client("stepfunctions")

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def handler(event, context):
    job_id = event["pathParameters"]["job_id"]
    index = int(event["pathParameters"]["index"])
    body = json.loads(event.get("body") or "{}")
    feedback = body.get("feedback", "")

    job = get_job(job_id)
    if not job:
        return _resp(404, {"error": "job not found"})
    slide = get_slide(job_id, index)
    if not slide:
        return _resp(404, {"error": "slide not found"})

    update_job_status(job_id, "retrying")
    _sf.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        input=json.dumps({
            "job_id": job_id,
            "index": index,
            "draft_text": slide.get("draft_text", ""),
            "feedback": feedback,
            "total": job.get("total_slides") or 1,
        }),
    )
    return _resp(202, {"job_id": job_id, "index": index, "status": "retrying"})


def _resp(code: int, body: dict):
    return {"statusCode": code, "headers": {"Content-Type": "application/json", **CORS}, "body": json.dumps(body)}
