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
- 단조로운 글머리 나열을 지양하라. 내용 성격에 맞춰 시각 구조를 적극 선택:
  * 대비/전후/장단/A vs B → "comparison"
  * 단계/절차/흐름 → "process"
  * 수치 비교·추세·비율 → "chart"
  * 항목 x 속성 격자 데이터 → "table"
  * 1~3개 핵심 지표 → "big_stat"
- 본문 슬라이드(bullets 외)에는 가능하면 데크 정체성을 위해
  breadcrumb(예: "Chapter 01 · 클라우드"), section(예: "DEFINITION"),
  takeaway(맨 아래 한 줄 핵심요약)를 채워라.
- 강조하고 싶은 핵심 구문은 *_highlights 배열에 '원문에 그대로 등장하는 부분 문자열'로
  지정하면 시스템이 강조색으로 칠한다(직접 색을 지정하지 말 것).
"""

ARCHETYPE_CATALOG = """\
아래 10개 아키타입 중 내용에 가장 잘 맞는 하나를 고르세요.
각 아키타입의 slots 구조를 정확히 따르세요(불필요한 슬롯은 생략 가능).

공통 본문 슬롯(아래 [본문] 표시 아키타입에서 사용 가능, 모두 선택):
  "eyebrow": str          // 대제목 위 작은 라벨 (예: "01 · 정의")
  "breadcrumb": str       // 상단 헤더 좌측 경로 (예: "Chapter 01 · 클라우드")
  "section": str          // 상단 헤더 우측 태그 (예: "DEFINITION")
  "lead": str             // 대제목 아래 도입 문장
  "lead_highlights": [str]// lead 안에서 강조할 부분 문자열들
  "takeaway": str         // 맨 아래 핵심요약 한 줄
  "footer_note": str      // 푸터 좌측 출처/조직명

1) "title" — 표지/대표 슬라이드 [전체화면]
   { "eyebrow"?, "title", "subtitle"? }

2) "section" — 장 구분/전환 (어두운 배경) [전체화면]
   { "number"?, "title", "subtitle"? }

3) "statement" — 한 문장 핵심 선언/인용 [전체화면]
   { "text", "highlights"?: [str], "attribution"? }

4) "bullets" — 제목 + 글머리 목록 [본문]
   { "title", "bullets": [str, ...], ...공통 }

5) "two_column" — 좌/우 2열 카드 (병렬 주제) [본문]
   { "title", "left": {"heading"?, "bullets":[str]}, "right": {...}, ...공통 }

6) "comparison" — 대비 (전/후, 장/단, A vs B). 라이트 vs 다크 카드 [본문]
   { "title",
     "left":  {"label", "heading", "heading_highlights"?:[str], "body", "chips":[str]},
     "right": {"label", "heading", "heading_highlights"?:[str], "body", "chips":[str]},
     ...공통 }

7) "big_stat" — 1~3개 핵심 수치 카드 [본문]
   { "title"?, "stats": [{"value","label"}], ...공통 }   // 최대 3개

8) "process" — 단계/절차 흐름 (가로 스텝 박스 + 화살표) [본문]
   { "title", "steps": [{"title","desc"?}], ...공통 }     // 최대 5개

9) "table" — 격자 데이터 표 [본문]
   { "title", "rows": [[셀,...], ...], "header"?: true, ...공통 }
   // rows[0]은 헤더 행

10) "chart" — 막대/꺾은선/원형 차트 [본문]
    { "title",
      "chart": {"type":"column"|"bar"|"line"|"pie",
                "categories":[str], "series":[{"name","values":[num]}]},
      ...공통 }
"""

OUTPUT_CONTRACT = """\
다음 형태의 단일 JSON 객체만 출력하세요 (코드펜스/설명/주석 금지):
{
  "archetype": "<위 10개 중 하나>",
  "slots": { ...선택한 아키타입의 슬롯... }
}

예시 (comparison — 대비 내용일 때 bullets 대신 이걸 써라):
{"archetype":"comparison","slots":{"eyebrow":"01 · 정의","breadcrumb":"Chapter 01 · 클라우드 컴퓨팅","section":"definition","title":"클라우드 컴퓨팅이란 무엇인가","lead":"인터넷을 통해 컴퓨팅 자원을 필요한 만큼, 필요한 시간만큼 사용하고 값을 지불하는 방식","lead_highlights":["필요한 만큼, 필요한 시간만큼","값을 지불"],"left":{"label":"On-Premises","heading":"자원을 소유한다","body":"서버 랙·케이블·방화벽을 직접 구성하고 관리하는 물리적 인프라","chips":["물리 구성","선투자(CapEx)","수동 확장"]},"right":{"label":"Cloud","heading":"자원을 호출한다","heading_highlights":["호출"],"body":"API 호출로 즉시 생성되는 자원. '빌린다'가 아니라 'API로 다룬다'는 의미","chips":["Infrastructure as Code","탄력적(OpEx)","자동 확장"]},"takeaway":"물리적 구성 대신 API로 자원을 다루는 것이 클라우드의 본질","footer_note":"Cloud Advisory"}}

예시 (process):
{"archetype":"process","slots":{"eyebrow":"흐름","title":"요청 처리 4단계","steps":[{"title":"수신","desc":"API 게이트웨이가 요청 접수"},{"title":"검증","desc":"인증·입력 검증"},{"title":"처리","desc":"비즈니스 로직 실행"},{"title":"응답","desc":"결과 반환"}]}}

예시 (chart):
{"archetype":"chart","slots":{"title":"분기별 매출 추이","chart":{"type":"column","categories":["Q1","Q2","Q3","Q4"],"series":[{"name":"매출","values":[12,19,25,31]}]},"takeaway":"4개 분기 연속 성장"}}
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
    return expand(_parse_json(text), {"page": index + 1, "total": total})


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    if start == -1:
        raise ValueError(f"Bedrock 응답에서 JSON을 찾을 수 없음: {text[:200]}")
    # 첫 번째 JSON 객체만 파싱(뒤에 설명/추가 객체가 붙어도 무시)
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
        return obj
    except json.JSONDecodeError:
        end = text.rfind("}")
        return json.loads(text[start : end + 1])
