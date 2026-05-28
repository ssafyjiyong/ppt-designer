import os

import boto3

from shared.ddb_client import put_slide_draft, update_job_status
from shared.pptx_builder import extract_drafts

BUCKET = os.environ["BUCKET"]
_s3 = boto3.client("s3")


def handler(event, context):
    job_id = event["job_id"]
    source_key = event["source_key"]
    obj = _s3.get_object(Bucket=BUCKET, Key=source_key)
    pptx_bytes = obj["Body"].read()

    drafts = extract_drafts(pptx_bytes)
    for i, text in enumerate(drafts):
        put_slide_draft(job_id, i, text)

    update_job_status(job_id, "designing", total_slides=len(drafts))
    return {
        "job_id": job_id,
        "total": len(drafts),
        "slides": [{"job_id": job_id, "index": i, "total": len(drafts), "draft_text": text} for i, text in enumerate(drafts)],
    }
