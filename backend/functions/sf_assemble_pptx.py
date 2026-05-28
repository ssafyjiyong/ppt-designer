import os

import boto3

from shared.ddb_client import list_slides, update_job_status
from shared.pptx_builder import build_pptx

BUCKET = os.environ["BUCKET"]
_s3 = boto3.client("s3")


def handler(event, context):
    job_id = event["job_id"]
    slides = list_slides(job_id)
    slides.sort(key=lambda s: s["index"])
    specs = [s.get("spec") or {} for s in slides]

    pptx_bytes = build_pptx(specs)
    result_key = f"results/{job_id}/designed.pptx"
    _s3.put_object(
        Bucket=BUCKET,
        Key=result_key,
        Body=pptx_bytes,
        ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
    update_job_status(job_id, "completed", result_key=result_key)
    return {"job_id": job_id, "result_key": result_key}
