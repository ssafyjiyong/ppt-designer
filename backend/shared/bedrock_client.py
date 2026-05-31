import json
import os
import re

import boto3

from shared.layouts import expand

_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")
_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "global.anthropic.claude-opus-4-6-v1")
_client = boto3.client("bedrock-runtime", region_name=_REGION)


DESIGN_SYSTEM = """\
당신은 시니어 프레젠테이션 디자이너입니다. 슬라이드의 메시지를 분석해
가장 효과적인 '레이아웃 아키타입'을 고르고, 그 슬롯에 들어갈 내용만 채웁니다.

좌표·색·폰트·정렬은 시스템이 12컬럼 그리드 위에서 자동 계산하므로
당신은 절대 좌표(x/y/w/h)나 색상 HEX를 출력하지 않습니다.
오직 '어떤 아키타입에 어떤 내용'인지만 결정하면 됩니다.

핵심 원칙:
- 한 슬라이드 = 하나의 핵심 메시지. 내용을 욱여넣지 말고 과감히 덜어낼 것.
- 원문 의미는 유지하되 문장은 짧고 명료하게 다듬는다(키워드/구문 위주).
- 글머리(bullet)는 슬라이드당 3~5개, 각 항목은 한 줄 분량으로.
- 슬라이드 위치를 고려: 보통 첫 장은 title, 장 전환은 section.
"""

ARCHETYPE_CATALOG = """\
아래 7개 아키타입 중 내용에 가장 잘 맞는 하나를 고르세요.
각 아키타입의 slots 구조를 정확히 따르세요(불필요한 슬롯은 생략 가능).

1) "title" — 표지/대표 슬라이드
   slots: { "eyebrow"?: str, "title": str, "subtitle"?: str }

2) "section" — 장 구분/전환 (어두운 배경, 강한 임팩트)
   slots: { "number"?: str, "title": str, "subtitle"?: str }

3) "statement" — 한 문장 핵심 선언/인용 (크게 중앙 배치)
   slots: { "text": str, "attribution"?: str }

4) "bullets" — 제목 + 글머리 목록 (가장 일반적인 본문)
   slots: { "title": str, "subtitle"?: str, "bullets": [str, ...] }

5) "two_column" — 제목 + 좌/우 2열 (병렬 주제, 대등 비교 아님)
   slots: { "title": str, "subtitle"?: str,
            "left":  { "heading"?: str, "bullets": [str, ...] },
            "right": { "heading"?: str, "bullets": [str, ...] } }

6) "comparison" — 대비 (전/후, 장/단, A vs B). 색 박스로 강조
   slots: { "title": str,
            "left":  { "heading": str, "points": [str, ...] },
            "right": { "heading": str, "points": [str, ...] } }

7) "big_stat" — 1~3개의 큰 수치/지표 강조
   slots: { "title"?: str,
            "stats": [ { "value": str, "label": str }, ... ] }  // 최대 3개
"""

OUTPUT_CONTRACT = """\
다음 형태의 단일 JSON 객체만 출력하세요 (코드펜스/설명/주석 금지):
{
  "archetype": "<위 7개 중 하나>",
  "slots": { ...선택한 아키타입의 슬롯... }
}

예시 (bullets):
{"archetype":"bullets","slots":{"title":"도입 배경","subtitle":"왜 지금인가","bullets":["시장 규모 연 30% 성장","기존 솔루션의 높은 운영 비용","규제 완화로 신규 진입 기회"]}}

예시 (comparison):
{"archetype":"comparison","slots":{"title":"도입 전후 비교","left":{"heading":"As-Is","points":["수작업 처리 3일","오류율 12%"]},"right":{"heading":"To-Be","points":["자동화 2시간","오류율 1%"]}}}
"""


def design_slide(draft_text: str, index: int, total: int) -> dict:
    position = "표지 슬라이드일 가능성이 높음" if index == 0 else "본문 슬라이드"
    user = f"""다음은 발표 슬라이드의 텍스트 초안입니다. 슬라이드 {index + 1}/{total} ({position}).

[초안]
{draft_text}

이 메시지에 가장 적합한 아키타입을 고르고 slots를 채워 JSON으로만 답하세요.
"""
    messages = [{"role": "user", "content": [{"type": "text", "text": user}]}]
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "temperature": 0.4,
        "system": DESIGN_SYSTEM + "\n\n" + ARCHETYPE_CATALOG + "\n\n" + OUTPUT_CONTRACT,
        "messages": messages,
    }
    resp = _client.invoke_model(
        modelId=_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    payload = json.loads(resp["body"].read())
    text = payload["content"][0]["text"]
    return expand(_parse_json(text))


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Bedrock 응답에서 JSON을 찾을 수 없음: {text[:200]}")
    return json.loads(text[start : end + 1])
