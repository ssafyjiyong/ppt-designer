from shared.bedrock_client import design_slide
from shared.ddb_client import put_slide_spec


def handler(event, context):
    job_id = event["job_id"]
    index = int(event["index"])
    total = int(event["total"])
    draft = event.get("draft_text", "")
    feedback = event.get("feedback", "")

    prompt_text = draft
    if feedback:
        prompt_text = f"{draft}\n\n[사용자 피드백 - 이번 재시도에 반영]\n{feedback}"

    spec = design_slide(prompt_text, index, total)
    put_slide_spec(job_id, index, spec)
    return {"job_id": job_id, "index": index, "ok": True}
