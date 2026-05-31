"""아키타입 기반 레이아웃 엔진.

LLM은 `archetype`(레이아웃 종류)과 `slots`(내용)만 결정한다.
좌표/색/타이포 위계는 모두 이 모듈이 12컬럼 그리드 위에서 계산하여
pptx_builder가 소비하는 flat 스펙 `{background, elements}`로 확장한다.

이렇게 LLM의 약점(절대좌표 배치)을 제거하고 강점(내용 구조화)만 사용한다.
"""

# --- 팔레트 (디자인 시스템과 1:1) ---
PRIMARY = "#1970DF"
PRIMARY_DARK = "#172A3D"
PURPLE_DARK = "#3F43AD"
PURPLE_MID = "#5949D3"
PURPLE_LIGHT = "#609EFF"
ACCENT_NEG = "#FB4C2E"
BG_LIGHT = "#F5F5F5"
BG_DARK = "#ECECEC"
BG_ACCENT = "#9EF06F"
WHITE = "#FFFFFF"

TEXT_BODY = PRIMARY_DARK   # 라이트 배경 본문
TEXT_ACCENT = PRIMARY      # 강조 텍스트
TEXT_MUTED = PURPLE_MID    # 보조 텍스트

# --- 그리드 ---
SLIDE_W = 13.333
SLIDE_H = 7.5
MARGIN_X = 0.5
MARGIN_Y = 0.4
GUTTER = 0.2
N_COLS = 12
CONTENT_W = SLIDE_W - 2 * MARGIN_X          # 12.333
CONTENT_H = SLIDE_H - 2 * MARGIN_Y          # 6.7
COL_W = (CONTENT_W - (N_COLS - 1) * GUTTER) / N_COLS


def col_x(start_col: int) -> float:
    """start_col(0~11)번 컬럼의 좌측 x 좌표."""
    return MARGIN_X + start_col * (COL_W + GUTTER)


def span_w(n_cols: int) -> float:
    """n_cols개 컬럼이 차지하는 폭(거터 포함)."""
    return n_cols * COL_W + (n_cols - 1) * GUTTER


# --- 요소 헬퍼 ---
def _text(text, x, y, w, h, size, color, *, bold=False, italic=False,
          align="left", valign="top"):
    return {
        "type": "text", "text": str(text), "x": round(x, 3), "y": round(y, 3),
        "w": round(w, 3), "h": round(h, 3), "font_size": int(size),
        "bold": bold, "italic": italic, "color": color,
        "align": align, "valign": valign,
    }


def _bullet(items, x, y, w, h, size, color):
    return {
        "type": "bullet", "items": [str(i) for i in items],
        "x": round(x, 3), "y": round(y, 3), "w": round(w, 3), "h": round(h, 3),
        "font_size": int(size), "color": color,
    }


def _rect(x, y, w, h, fill, *, shape="rectangle", line=None, line_w=1):
    return {
        "type": "shape", "shape": shape,
        "x": round(x, 3), "y": round(y, 3), "w": round(w, 3), "h": round(h, 3),
        "fill": fill, "line": line, "line_w": line_w,
    }


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [v for v in value if str(v).strip()]
    return [value]


# --- 아키타입 ---
def _title(slots):
    els = []
    eyebrow = slots.get("eyebrow")
    subtitle = slots.get("subtitle")
    tx = MARGIN_X + 0.45
    tw = span_w(10)
    els.append(_rect(MARGIN_X, 2.75, 0.14, 1.9, PRIMARY))
    if eyebrow:
        els.append(_text(eyebrow, tx, 2.5, tw, 0.5, 16, TEXT_ACCENT,
                         bold=True, valign="bottom"))
    els.append(_text(slots.get("title", ""), tx, 3.0, tw, 1.3, 40, TEXT_BODY,
                     bold=True, valign="middle"))
    if subtitle:
        els.append(_text(subtitle, tx, 4.45, span_w(9), 1.0, 20, TEXT_MUTED))
    return BG_LIGHT, els


def _section(slots):
    els = []
    tx = MARGIN_X + 0.3
    number = slots.get("number")
    subtitle = slots.get("subtitle")
    if number:
        els.append(_text(number, tx, 2.0, span_w(6), 0.8, 28, PURPLE_LIGHT, bold=True))
    els.append(_rect(tx, 2.62, 1.3, 0.1, BG_ACCENT))
    els.append(_text(slots.get("title", ""), tx, 2.9, span_w(11), 1.4, 40, WHITE,
                     bold=True, valign="middle"))
    if subtitle:
        els.append(_text(subtitle, tx, 4.45, span_w(9), 1.0, 20, PURPLE_LIGHT))
    return PRIMARY_DARK, els


def _statement(slots):
    els = []
    attribution = slots.get("attribution")
    els.append(_text(slots.get("text", ""), col_x(1), 2.3, span_w(10), 2.0, 32,
                     TEXT_BODY, bold=True, align="center", valign="middle"))
    els.append(_rect((SLIDE_W - 1.2) / 2, 4.45, 1.2, 0.08, PRIMARY))
    if attribution:
        els.append(_text(attribution, col_x(2), 4.7, span_w(8), 0.6, 18,
                         TEXT_MUTED, italic=True, align="center"))
    return BG_LIGHT, els


def _header(els, title, subtitle):
    """라이트 슬라이드 상단 공통 헤더. 본문 시작 y를 반환."""
    els.append(_text(title, col_x(0), 0.55, span_w(12), 0.95, 32, TEXT_BODY, bold=True))
    els.append(_rect(MARGIN_X, 1.6, 1.5, 0.08, PRIMARY))
    if subtitle:
        els.append(_text(subtitle, col_x(0), 1.78, span_w(11), 0.55, 18, TEXT_MUTED))
        return 2.55
    return 2.05


def _bullets(slots):
    els = []
    body_y = _header(els, slots.get("title", ""), slots.get("subtitle"))
    items = _as_list(slots.get("bullets"))
    els.append(_bullet(items, col_x(0), body_y, span_w(11), SLIDE_H - MARGIN_Y - body_y,
                       18, TEXT_BODY))
    return BG_LIGHT, els


def _column(els, side_x, body_y, col):
    heading = col.get("heading")
    cw = span_w(6)
    y = body_y
    if heading:
        els.append(_text(heading, side_x, y, cw, 0.6, 20, TEXT_ACCENT, bold=True))
        y += 0.75
    els.append(_bullet(_as_list(col.get("bullets") or col.get("body")),
                       side_x, y, cw, SLIDE_H - MARGIN_Y - y, 16, TEXT_BODY))


def _two_column(slots):
    els = []
    body_y = _header(els, slots.get("title", ""), slots.get("subtitle"))
    _column(els, col_x(0), body_y, slots.get("left") or {})
    _column(els, col_x(6), body_y, slots.get("right") or {})
    return BG_LIGHT, els


def _comparison(slots):
    els = []
    body_y = _header(els, slots.get("title", ""), None)
    box_h = SLIDE_H - MARGIN_Y - body_y
    pad = 0.3
    for side_x, fill, col in (
        (col_x(0), PRIMARY, slots.get("left") or {}),
        (col_x(6), PURPLE_MID, slots.get("right") or {}),
    ):
        cw = span_w(6)
        els.append(_rect(side_x, body_y, cw, box_h, fill, shape="rounded_rectangle"))
        els.append(_text(col.get("heading", ""), side_x + pad, body_y + pad,
                         cw - 2 * pad, 0.7, 22, WHITE, bold=True))
        els.append(_bullet(_as_list(col.get("points") or col.get("bullets")),
                           side_x + pad, body_y + pad + 0.85,
                           cw - 2 * pad, box_h - pad - 0.85 - pad, 16, WHITE))
    return BG_LIGHT, els


def _big_stat(slots):
    els = []
    title = slots.get("title")
    body_y = _header(els, title, None) if title else 1.6
    stats = (slots.get("stats") or [])[:3]
    n = max(len(stats), 1)
    card_gap = 0.3
    card_w = (CONTENT_W - (n - 1) * card_gap) / n
    card_y = body_y + 0.4
    card_h = SLIDE_H - MARGIN_Y - card_y
    cycle = [PRIMARY, PURPLE_MID, PURPLE_DARK]
    for i, stat in enumerate(stats):
        x = MARGIN_X + i * (card_w + card_gap)
        els.append(_rect(x, card_y, card_w, card_h, BG_DARK, shape="rounded_rectangle"))
        els.append(_text(stat.get("value", ""), x, card_y + card_h * 0.18,
                         card_w, card_h * 0.4, 48, cycle[i % 3],
                         bold=True, align="center", valign="middle"))
        els.append(_text(stat.get("label", ""), x + 0.25, card_y + card_h * 0.62,
                         card_w - 0.5, card_h * 0.28, 16, TEXT_BODY,
                         align="center", valign="top"))
    return BG_LIGHT, els


_ARCHETYPES = {
    "title": _title,
    "section": _section,
    "statement": _statement,
    "bullets": _bullets,
    "two_column": _two_column,
    "comparison": _comparison,
    "big_stat": _big_stat,
}


def expand(spec: dict) -> dict:
    """LLM 출력(`{archetype, slots}`)을 flat 렌더 스펙으로 확장.

    - 알려진 아키타입이면 좌표/색을 계산해 elements 생성.
    - 이미 elements를 직접 담은 구버전 스펙이면 그대로 통과(하위 호환).
    - 그 외에는 bullets 아키타입으로 폴백.
    """
    if not isinstance(spec, dict):
        return {"background": {"color": BG_LIGHT}, "elements": []}

    if "elements" in spec and "archetype" not in spec:
        bg = spec.get("background") or {"color": BG_LIGHT}
        return {"background": bg, "elements": spec["elements"]}

    archetype = spec.get("archetype", "bullets")
    slots = spec.get("slots") or {}
    fn = _ARCHETYPES.get(archetype, _bullets)
    bg_color, elements = fn(slots)
    return {"background": {"color": bg_color}, "elements": elements}
