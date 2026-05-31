"""아키타입 기반 레이아웃 엔진.

LLM은 `archetype`(레이아웃 종류)과 `slots`(내용)만 결정한다.
좌표/색/타이포 위계, 데크 크롬(헤더·푸터), 카드·칩·키워드 강조는 모두 이
모듈이 12컬럼 그리드 위에서 계산하여 pptx_builder가 소비하는 flat 스펙
`{background, elements}`로 확장한다.

LLM의 약점(절대좌표 배치)을 제거하고 강점(내용 구조화)만 사용한다.
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
CARD = "#FFFFFF"          # 라이트 배경 위 카드(흰색이 #F5F5F5 위에서 떠 보임)

TEXT_BODY = PRIMARY_DARK   # 라이트 배경 본문
TEXT_ACCENT = PRIMARY      # 강조 텍스트/키워드
TEXT_MUTED = PURPLE_MID    # 보조 텍스트

BRAND = ""                 # 데크 브랜드(상단 좌측). 비우면 breadcrumb만 표시.

# --- 그리드 ---
SLIDE_W = 13.333
SLIDE_H = 7.5
MARGIN_X = 0.5
MARGIN_Y = 0.4
GUTTER = 0.2
N_COLS = 12
CONTENT_W = SLIDE_W - 2 * MARGIN_X          # 12.333
COL_W = (CONTENT_W - (N_COLS - 1) * GUTTER) / N_COLS

# 크롬(헤더/푸터)이 있는 본문 슬라이드의 세로 영역
HEADER_RULE_Y = 0.78
FOOTER_RULE_Y = 7.02
PAD = 0.32                                  # 카드 안쪽 여백


def col_x(start_col):
    return MARGIN_X + start_col * (COL_W + GUTTER)


def span_w(n_cols):
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


def _rtext(runs, x, y, w, h, size, color, *, align="left", valign="top"):
    return {
        "type": "text", "runs": runs, "text": "".join(str(r.get("text", "")) for r in runs),
        "x": round(x, 3), "y": round(y, 3), "w": round(w, 3), "h": round(h, 3),
        "font_size": int(size), "color": color, "align": align, "valign": valign,
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


def _emphasize(text, highlights, base_color, accent_color, size):
    """문장 안의 특정 구문(highlights)만 accent_color+bold로 칠한 runs 리스트."""
    text = str(text)
    hl = sorted({h for h in (highlights or []) if h and h in text}, key=len, reverse=True)
    if not hl:
        return [{"text": text, "color": base_color, "size": size}]
    runs = [{"text": text}]
    for phrase in hl:
        new = []
        for r in runs:
            if r.get("hl") or phrase not in r["text"]:
                new.append(r)
                continue
            seg = r["text"]
            idx = seg.find(phrase)
            if seg[:idx]:
                new.append({"text": seg[:idx]})
            new.append({"text": phrase, "hl": True})
            if seg[idx + len(phrase):]:
                new.append({"text": seg[idx + len(phrase):]})
        runs = new
    out = []
    for r in runs:
        if r.get("hl"):
            out.append({"text": r["text"], "color": accent_color, "bold": True, "size": size})
        else:
            out.append({"text": r["text"], "color": base_color, "size": size})
    return out


def _chip_row(els, x, y, labels, *, fill, text_color, max_w, accent_fill=None,
              accent_text=None, height=0.42, gap=0.15, size=12):
    labels = [str(l) for l in labels]
    if not labels:
        return
    widths = [max(0.7, 0.34 + len(l) * 0.15) for l in labels]
    total = sum(widths) + gap * (len(labels) - 1)
    if total > max_w:                       # 카드 폭을 넘으면 균등 축소
        scale = (max_w - gap * (len(labels) - 1)) / sum(widths)
        widths = [w * scale for w in widths]
    cx = x
    for i, (label, w) in enumerate(zip(labels, widths)):
        f, tc = fill, text_color
        if i == 0 and accent_fill:
            f, tc = accent_fill, (accent_text or text_color)
        els.append(_rect(cx, y, w, height, f, shape="rounded_rectangle"))
        els.append(_text(label, cx, y, w, height, size, tc, align="center", valign="middle"))
        cx += w + gap


# --- 데크 크롬 ---
def _chrome(els, slots, ctx):
    """상단 헤더(로고·브레드크럼·섹션) + 하단 푸터(출처·페이지). 본문 슬라이드용."""
    els.append(_rect(MARGIN_X, 0.33, 0.26, 0.26, PRIMARY))
    brand = slots.get("brand") or BRAND
    crumb = slots.get("breadcrumb") or ""
    left = f"{brand}    /    {crumb}" if (brand and crumb) else (brand or crumb)
    if left:
        els.append(_text(left, MARGIN_X + 0.4, 0.3, span_w(9), 0.34, 12,
                         TEXT_BODY, bold=True, valign="middle"))
    section = slots.get("section")
    if section:
        els.append(_text(str(section).upper(), col_x(0), 0.3, span_w(12), 0.34, 12,
                         TEXT_ACCENT, bold=True, align="right", valign="middle"))
    els.append(_rect(MARGIN_X, HEADER_RULE_Y, CONTENT_W, 0.014, BG_DARK))

    els.append(_rect(MARGIN_X, FOOTER_RULE_Y, CONTENT_W, 0.014, BG_DARK))
    note = slots.get("footer_note")
    if note:
        els.append(_text(note, MARGIN_X, 7.08, span_w(9), 0.3, 10, TEXT_MUTED, valign="middle"))
    if ctx and ctx.get("total"):
        els.append(_text(f"{ctx.get('page', '')} / {ctx['total']}", col_x(0), 7.08,
                         span_w(12), 0.3, 10, TEXT_MUTED, align="right", valign="middle"))


def _body_head(els, slots):
    """본문 슬라이드 상단: eyebrow + 대제목 + (선택)리드문. 본문 시작 y 반환."""
    eyebrow = slots.get("eyebrow")
    y = 1.0
    if eyebrow:
        els.append(_text(eyebrow, col_x(0), 0.98, span_w(9), 0.36, 14, TEXT_ACCENT, bold=True))
        y = 1.36
    els.append(_text(slots.get("title", ""), col_x(0), y, span_w(12), 0.9, 32, TEXT_BODY, bold=True))
    y += 1.0
    lead = slots.get("lead")
    if lead:
        runs = _emphasize(lead, slots.get("lead_highlights"), TEXT_BODY, TEXT_ACCENT, 18)
        els.append(_rtext(runs, col_x(0), y, span_w(11), 0.9, 18, TEXT_BODY))
        y += 1.0
    return y + 0.15


def _takeaway(els, slots):
    """하단 핵심요약 콜아웃. 본문 영역 하한 y 반환."""
    t = slots.get("takeaway")
    if not t:
        return 6.85
    runs = [{"text": "▶  ", "color": TEXT_ACCENT, "bold": True, "size": 13}]
    runs += _emphasize(t, slots.get("takeaway_highlights"), TEXT_BODY, TEXT_ACCENT, 13)
    els.append(_rtext(runs, col_x(0), 6.5, span_w(12), 0.4, 13, TEXT_BODY, valign="middle"))
    return 6.35


# --- 아키타입 (full-bleed: 표지/전환) ---
def _title(slots):
    els = []
    tx = MARGIN_X + 0.45
    els.append(_rect(MARGIN_X, 2.75, 0.14, 1.9, PRIMARY))
    if slots.get("eyebrow"):
        els.append(_text(slots["eyebrow"], tx, 2.5, span_w(10), 0.5, 16, TEXT_ACCENT,
                         bold=True, valign="bottom"))
    els.append(_text(slots.get("title", ""), tx, 3.0, span_w(10), 1.3, 40, TEXT_BODY,
                     bold=True, valign="middle"))
    if slots.get("subtitle"):
        els.append(_text(slots["subtitle"], tx, 4.45, span_w(9), 1.0, 20, TEXT_MUTED))
    return BG_LIGHT, els


def _section(slots):
    els = []
    tx = MARGIN_X + 0.3
    if slots.get("number"):
        els.append(_text(slots["number"], tx, 2.0, span_w(6), 0.8, 28, PURPLE_LIGHT, bold=True))
    els.append(_rect(tx, 2.62, 1.3, 0.1, BG_ACCENT))
    els.append(_text(slots.get("title", ""), tx, 2.9, span_w(11), 1.4, 40, WHITE,
                     bold=True, valign="middle"))
    if slots.get("subtitle"):
        els.append(_text(slots["subtitle"], tx, 4.45, span_w(9), 1.0, 20, PURPLE_LIGHT))
    return PRIMARY_DARK, els


def _statement(slots):
    els = []
    runs = _emphasize(slots.get("text", ""), slots.get("highlights"),
                      TEXT_BODY, TEXT_ACCENT, 32)
    for r in runs:
        r["bold"] = True
    els.append(_rtext(runs, col_x(1), 2.3, span_w(10), 2.0, 32, TEXT_BODY,
                      align="center", valign="middle"))
    els.append(_rect((SLIDE_W - 1.2) / 2, 4.45, 1.2, 0.08, PRIMARY))
    if slots.get("attribution"):
        els.append(_text(slots["attribution"], col_x(2), 4.7, span_w(8), 0.6, 18,
                         TEXT_MUTED, italic=True, align="center"))
    return BG_LIGHT, els


# --- 아키타입 (본문: 크롬 포함) ---
def _bullets(slots, ctx):
    els = []
    _chrome(els, slots, ctx)
    body_y = _body_head(els, slots)
    bottom = _takeaway(els, slots)
    els.append(_bullet(_as_list(slots.get("bullets")), col_x(0), body_y,
                       span_w(11), bottom - body_y, 18, TEXT_BODY))
    return BG_LIGHT, els


def _two_column(slots, ctx):
    els = []
    _chrome(els, slots, ctx)
    body_y = _body_head(els, slots)
    bottom = _takeaway(els, slots)
    h = bottom - body_y
    for side_x, col in ((col_x(0), slots.get("left") or {}),
                        (col_x(6), slots.get("right") or {})):
        cw = span_w(6)
        els.append(_rect(side_x, body_y, cw, h, CARD, shape="rounded_rectangle", line=BG_DARK))
        iy = body_y + PAD
        if col.get("heading"):
            els.append(_text(col["heading"], side_x + PAD, iy, cw - 2 * PAD, 0.55, 19,
                             TEXT_ACCENT, bold=True))
            iy += 0.7
        els.append(_bullet(_as_list(col.get("bullets") or col.get("body")),
                           side_x + PAD, iy, cw - 2 * PAD, h - (iy - body_y) - PAD, 15, TEXT_BODY))
    return BG_LIGHT, els


def _comparison(slots, ctx):
    els = []
    _chrome(els, slots, ctx)
    body_y = _body_head(els, slots)
    bottom = _takeaway(els, slots)
    h = bottom - body_y
    cw = span_w(6)
    sides = [
        (col_x(0), CARD, BG_DARK, slots.get("left") or {},
         TEXT_MUTED, TEXT_BODY, PRIMARY, TEXT_BODY, BG_DARK, PRIMARY_DARK, PRIMARY, WHITE),
        (col_x(6), PRIMARY_DARK, None, slots.get("right") or {},
         PURPLE_LIGHT, WHITE, BG_ACCENT, BG_DARK, PURPLE_DARK, WHITE, BG_ACCENT, PRIMARY_DARK),
    ]
    for (x, fill, border, col, label_c, head_c, head_accent, body_c,
         chip_fill, chip_text, achip_fill, achip_text) in sides:
        els.append(_rect(x, body_y, cw, h, fill, shape="rounded_rectangle", line=border))
        ix = x + PAD
        iw = cw - 2 * PAD
        if col.get("label"):
            els.append(_text(str(col["label"]).upper(), ix, body_y + 0.3, iw, 0.35, 12,
                             label_c, bold=True))
        head_runs = _emphasize(col.get("heading", ""), col.get("heading_highlights"),
                               head_c, head_accent, 23)
        for r in head_runs:
            r["bold"] = True
        els.append(_rtext(head_runs, ix, body_y + 0.66, iw, 0.7, 23, head_c))
        els.append(_rect(ix, body_y + 1.42, iw, 0.014, chip_fill))
        body = col.get("body") or "  ".join(_as_list(col.get("points") or col.get("bullets")))
        if body:
            els.append(_text(body, ix, body_y + 1.6, iw, h - 2.5, 15, body_c))
        chips = _as_list(col.get("chips"))
        if chips:
            _chip_row(els, ix, body_y + h - 0.72, chips, fill=chip_fill, text_color=chip_text,
                      accent_fill=achip_fill, accent_text=achip_text, max_w=iw, size=12)
    return BG_LIGHT, els


def _big_stat(slots, ctx):
    els = []
    _chrome(els, slots, ctx)
    body_y = _body_head(els, slots)
    bottom = _takeaway(els, slots)
    stats = (slots.get("stats") or [])[:3]
    n = max(len(stats), 1)
    gap = 0.3
    card_w = (CONTENT_W - (n - 1) * gap) / n
    card_h = bottom - body_y
    cycle = [PRIMARY, PURPLE_MID, PURPLE_DARK]
    for i, stat in enumerate(stats):
        x = MARGIN_X + i * (card_w + gap)
        c = cycle[i % 3]
        els.append(_rect(x, body_y, card_w, card_h, CARD, shape="rounded_rectangle", line=BG_DARK))
        els.append(_rect(x, body_y, card_w, 0.12, c, shape="rectangle"))
        els.append(_text(stat.get("value", ""), x, body_y + card_h * 0.2, card_w,
                         card_h * 0.4, 48, c, bold=True, align="center", valign="middle"))
        els.append(_text(stat.get("label", ""), x + 0.25, body_y + card_h * 0.66,
                         card_w - 0.5, card_h * 0.28, 16, TEXT_BODY, align="center"))
    return BG_LIGHT, els


def _table(slots, ctx):
    els = []
    _chrome(els, slots, ctx)
    body_y = _body_head(els, slots)
    bottom = _takeaway(els, slots)
    rows = slots.get("rows") or []
    n_rows = max(len(rows), 1)
    h = min(bottom - body_y, 0.62 * n_rows + 0.2)
    els.append({
        "type": "table", "rows": rows, "header": bool(slots.get("header", True)),
        "x": round(col_x(0), 3), "y": round(body_y, 3),
        "w": round(span_w(12), 3), "h": round(h, 3),
        "font_size": 14, "header_fill": PRIMARY, "header_color": WHITE,
        "body_color": TEXT_BODY,
    })
    return BG_LIGHT, els


def _process(slots, ctx):
    els = []
    _chrome(els, slots, ctx)
    body_y = _body_head(els, slots)
    bottom = _takeaway(els, slots)
    steps = (slots.get("steps") or [])[:5]
    n = max(len(steps), 1)
    arrow = 0.5
    box_w = (CONTENT_W - (n - 1) * arrow) / n
    box_h = min(2.6, bottom - body_y)
    box_y = body_y + (bottom - body_y - box_h) / 2
    cycle = [PRIMARY, PURPLE_MID, PURPLE_DARK, PRIMARY_DARK]
    for i, step in enumerate(steps):
        x = MARGIN_X + i * (box_w + arrow)
        c = cycle[i % len(cycle)]
        els.append(_rect(x, box_y, box_w, box_h, CARD, shape="rounded_rectangle", line=BG_DARK))
        els.append(_rect(x + PAD, box_y + 0.28, 0.5, 0.5, c, shape="oval"))
        els.append(_text(str(i + 1), x + PAD, box_y + 0.28, 0.5, 0.5, 18, WHITE,
                         bold=True, align="center", valign="middle"))
        els.append(_text(step.get("title", ""), x + PAD, box_y + 0.95, box_w - 2 * PAD,
                         0.6, 17, TEXT_BODY, bold=True))
        if step.get("desc"):
            els.append(_text(step["desc"], x + PAD, box_y + 1.55, box_w - 2 * PAD,
                             box_h - 1.7, 13, TEXT_MUTED))
        if i < n - 1:
            els.append(_text("→", x + box_w, box_y, arrow, box_h, 24, PRIMARY,
                             align="center", valign="middle"))
    return BG_LIGHT, els


def _chart(slots, ctx):
    els = []
    _chrome(els, slots, ctx)
    body_y = _body_head(els, slots)
    bottom = _takeaway(els, slots)
    chart = slots.get("chart") or {}
    els.append({
        "type": "chart",
        "chart_type": chart.get("type", "column"),
        "categories": chart.get("categories") or [],
        "series": chart.get("series") or [],
        "colors": chart.get("colors") or [PRIMARY, PURPLE_MID, PURPLE_LIGHT, BG_ACCENT],
        "legend": chart.get("legend"),
        "x": round(col_x(0), 3), "y": round(body_y, 3),
        "w": round(span_w(12), 3), "h": round(bottom - body_y, 3),
    })
    return BG_LIGHT, els


_FULLBLEED = {"title": _title, "section": _section, "statement": _statement}
_BODY = {
    "bullets": _bullets,
    "two_column": _two_column,
    "comparison": _comparison,
    "big_stat": _big_stat,
    "table": _table,
    "process": _process,
    "chart": _chart,
}


def expand(spec, ctx=None):
    """LLM 출력(`{archetype, slots}`)을 flat 렌더 스펙으로 확장.

    - 알려진 아키타입이면 좌표/색/크롬을 계산해 elements 생성.
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
    if archetype in _FULLBLEED:
        bg_color, elements = _FULLBLEED[archetype](slots)
    else:
        fn = _BODY.get(archetype, _bullets)
        bg_color, elements = fn(slots, ctx or {})
    return {"background": {"color": bg_color}, "elements": elements}
