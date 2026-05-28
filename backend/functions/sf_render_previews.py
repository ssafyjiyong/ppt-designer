import glob
import os
import re
import subprocess
import tempfile

import boto3

from shared.ddb_client import put_slide_preview

BUCKET = os.environ["BUCKET"]
_s3 = boto3.client("s3")


def _page_num(path: str) -> int:
    m = re.search(r"slide-(\d+)\.png$", path)
    return int(m.group(1)) if m else 0


def handler(event, context):
    job_id = event["job_id"]
    result_key = f"results/{job_id}/designed.pptx"

    with tempfile.TemporaryDirectory(dir="/tmp") as tmpdir:
        pptx_path = os.path.join(tmpdir, "designed.pptx")
        _s3.download_file(BUCKET, result_key, pptx_path)

        env = {**os.environ, "HOME": "/tmp"}
        subprocess.run(
            ["soffice", "--headless", "--nologo", "--norestore",
             "--convert-to", "pdf", "--outdir", tmpdir, pptx_path],
            check=True, env=env, timeout=180,
        )
        pdf_path = os.path.join(tmpdir, "designed.pdf")

        png_prefix = os.path.join(tmpdir, "slide")
        subprocess.run(
            ["pdftoppm", "-png", "-r", "150", pdf_path, png_prefix],
            check=True, timeout=180,
        )

        png_files = sorted(glob.glob(os.path.join(tmpdir, "slide-*.png")), key=_page_num)
        preview_keys = []
        for i, fn in enumerate(png_files):
            key = f"previews/{job_id}/slide-{i:03d}.png"
            _s3.upload_file(
                fn, BUCKET, key,
                ExtraArgs={"ContentType": "image/png", "CacheControl": "no-cache"},
            )
            put_slide_preview(job_id, i, key)
            preview_keys.append(key)

    return {"job_id": job_id, "count": len(preview_keys)}
