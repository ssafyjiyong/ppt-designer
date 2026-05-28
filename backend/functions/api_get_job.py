import json
import os

import boto3
from botocore.client import Config

from shared.ddb_client import get_job, list_slides

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
    job_id = event["pathParameters"]["job_id"]
    job = get_job(job_id)
    if not job:
        return _resp(404, {"error": "job not found"})

    slides = list_slides(job_id)
    slides.sort(key=lambda s: s["index"])
    response_slides = []
    for s in slides:
        spec = s.get("spec") or {}
        response_slides.append({
            "index": s["index"],
            "draft_text": s.get("draft_text", ""),
            "designed": bool(s.get("designed_at")),
            "title": _extract_title(spec),
            "spec": spec if s.get("designed_at") else None,
        })

    download_url = None
    if job.get("status") == "completed" and job.get("result_key"):
        download_url = _s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": job["result_key"]},
            ExpiresIn=3600,
        )

    return _resp(200, {
        "job_id": job_id,
        "status": job.get("status"),
        "error": job.get("error"),
        "total_slides": job.get("total_slides"),
        "slides": response_slides,
        "download_url": download_url,
    })


def _extract_title(spec: dict) -> str:
    for el in (spec or {}).get("elements", []):
        if el.get("type") == "text" and (el.get("font_size") or 0) >= 24:
            return (el.get("text") or "")[:80]
    for el in (spec or {}).get("elements", []):
        if el.get("type") == "text":
            return (el.get("text") or "")[:80]
    return ""


def _resp(code: int, body: dict):
    return {"statusCode": code, "headers": {"Content-Type": "application/json", **CORS}, "body": json.dumps(body, default=str)}
