import json
import os
import re

import boto3

_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")
_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "apac.anthropic.claude-sonnet-4-5-20250929-v1:0")
_client = boto3.client("bedrock-runtime", region_name=_REGION)


DESIGN_SYSTEM = """\
디자인 시스템 (반드시 준수):
- 슬라이드 크기: 13.333 inch (가로) x 7.5 inch (세로) — 16:9
- 안전 여백: 좌우 0.5, 상하 0.4
- 12 컬럼 그리드 기준 좌표 사용
- 컬러 팔레트 (이 중에서만 선택):
  * primary: #1970DF
  * primary_dark: #172A3D
  * purple_dark: #3F43AD
  * purple_mid: #5949D3
  * purple_light: #609EFF
  * accent_negative: #FB4C2E
  * background_light: #F5F5F5
  * background_dark: #ECECEC
  * background_accent: #9EF06F
- 폰트: 'Pretendard' (없으면 'Malgun Gothic'). title 28~40pt, subtitle 18~22pt, body 12~16pt
- 모든 좌표 단위는 inch, 모든 색은 위 팔레트의 HEX
"""

OUTPUT_CONTRACT = """\
다음 JSON 스키마를 정확히 따르는 단일 JSON 객체만 출력 (코드펜스/설명 금지):
{
  "background": {"color": "#HEXCOLOR"},
  "elements": [
    {
      "type": "text",
      "text": "내용",
      "x": 숫자, "y": 숫자, "w": 숫자, "h": 숫자,
      "font_size": 정수, "bold": true|false, "italic": true|false,
      "color": "#HEXCOLOR", "align": "left"|"center"|"right",
      "valign": "top"|"middle"|"bottom"
    },
    {
      "type": "shape",
      "shape": "rectangle"|"rounded_rectangle"|"oval"|"line",
      "x": 숫자, "y": 숫자, "w": 숫자, "h": 숫자,
      "fill": "#HEXCOLOR"|null, "line": "#HEXCOLOR"|null, "line_w": 숫자
    },
    {
      "type": "bullet",
      "items": ["항목1", "항목2"],
      "x": 숫자, "y": 숫자, "w": 숫자, "h": 숫자,
      "font_size": 정수, "color": "#HEXCOLOR"
    }
  ]
}
"""


def design_slide(draft_text: str, index: int, total: int) -> dict:
    user = f"""다음은 발표 슬라이드의 텍스트 초안입니다. 슬라이드 {index + 1}/{total}.

[초안]
{draft_text}

이 슬라이드의 메시지를 가장 잘 전달할 레이아웃을 생성하세요.
- 제목/소제목/본문/강조 요소를 적절히 배치
- 본문이 길면 bullet 또는 분할 영역으로 가독성 확보
- 핵심 키워드는 박스/색상 강조
- 불필요한 텍스트는 다듬어 간결하게 (원문 의미는 유지)
"""
    messages = [{"role": "user", "content": [{"type": "text", "text": user}]}]
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "temperature": 0.7,
        "system": DESIGN_SYSTEM + "\n\n" + OUTPUT_CONTRACT,
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
    return _parse_json(text)


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
