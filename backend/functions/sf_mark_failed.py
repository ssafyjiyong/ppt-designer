import json

from shared.ddb_client import update_job_status


def handler(event, context):
    job_id = event["job_id"]
    err = event.get("error", {})
    msg = json.dumps(err)[:1000] if not isinstance(err, str) else err[:1000]
    update_job_status(job_id, "failed", error=msg)
    return {"job_id": job_id, "status": "failed"}
