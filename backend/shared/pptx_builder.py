import io
import re

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

SLIDE_W = 13.333
SLIDE_H = 7.5

_ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}
_ANCHOR = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}
_SHAPE = {
    "rectangle": MSO_SHAPE.RECTANGLE,
    "rounded_rectangle": MSO_SHAPE.ROUNDED_RECTANGLE,
    "oval": MSO_SHAPE.OVAL,
}


def _hex_to_rgb(h: str) -> RGBColor:
    if not h:
        return RGBColor(0, 0, 0)
    h = h.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        return RGBColor(0, 0, 0)
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _new_presentation() -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    return prs


def _blank_layout(prs: Presentation):
    return prs.slide_layouts[6]


def _add_text(slide, el: dict):
    box = slide.shapes.add_textbox(
        Inches(float(el["x"])), Inches(float(el["y"])),
        Inches(float(el["w"])), Inches(float(el["h"])),
    )
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = _ANCHOR.get(el.get("valign", "top"), MSO_ANCHOR.TOP)
    p = tf.paragraphs[0]
    p.alignment = _ALIGN.get(el.get("align", "left"), PP_ALIGN.LEFT)
    run = p.add_run()
    run.text = el.get("text", "")
    f = run.font
    f.size = Pt(int(el.get("font_size", 16)))
    f.bold = bool(el.get("bold", False))
    f.italic = bool(el.get("italic", False))
    f.color.rgb = _hex_to_rgb(el.get("color", "#1A1A1A"))
    f.name = el.get("font_name", "Pretendard")


def _add_bullet(slide, el: dict):
    box = slide.shapes.add_textbox(
        Inches(float(el["x"])), Inches(float(el["y"])),
        Inches(float(el["w"])), Inches(float(el["h"])),
    )
    tf = box.text_frame
    tf.word_wrap = True
    items = el.get("items", [])
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = f"• {item}"
        run.font.size = Pt(int(el.get("font_size", 14)))
        run.font.color.rgb = _hex_to_rgb(el.get("color", "#1A1A1A"))
        run.font.name = el.get("font_name", "Pretendard")


def _add_shape(slide, el: dict):
    shape_type = el.get("shape", "rectangle")
    if shape_type == "line":
        from pptx.util import Emu
        x1 = Inches(float(el["x"]))
        y1 = Inches(float(el["y"]))
        x2 = Inches(float(el["x"]) + float(el["w"]))
        y2 = Inches(float(el["y"]) + float(el["h"]))
        connector = slide.shapes.add_connector(1, x1, y1, x2, y2)
        connector.line.color.rgb = _hex_to_rgb(el.get("line") or "#1A1A1A")
        connector.line.width = Pt(float(el.get("line_w", 1)))
        return
    mso_shape = _SHAPE.get(shape_type, MSO_SHAPE.RECTANGLE)
    shp = slide.shapes.add_shape(
        mso_shape,
        Inches(float(el["x"])), Inches(float(el["y"])),
        Inches(float(el["w"])), Inches(float(el["h"])),
    )
    fill = el.get("fill")
    if fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = _hex_to_rgb(fill)
    else:
        shp.fill.background()
    line = el.get("line")
    if line:
        shp.line.color.rgb = _hex_to_rgb(line)
        shp.line.width = Pt(float(el.get("line_w", 1)))
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False


def _apply_background(slide, bg: dict):
    color_hex = (bg or {}).get("color", "#FFFFFF")
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = _hex_to_rgb(color_hex)


def _render_slide(slide, spec: dict):
    _apply_background(slide, spec.get("background", {}))
    for el in spec.get("elements", []):
        try:
            t = el.get("type")
            if t == "text":
                _add_text(slide, el)
            elif t == "bullet":
                _add_bullet(slide, el)
            elif t == "shape":
                _add_shape(slide, el)
        except Exception as e:
            print(f"[render] element skip: {e} / el={el}")


def build_pptx(specs: list) -> bytes:
    prs = _new_presentation()
    layout = _blank_layout(prs)
    for spec in specs:
        slide = prs.slides.add_slide(layout)
        _render_slide(slide, spec or {})
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def extract_drafts(pptx_bytes: bytes) -> list:
    prs = Presentation(io.BytesIO(pptx_bytes))
    drafts = []
    for slide in prs.slides:
        parts = []
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for p in shape.text_frame.paragraphs:
                line = "".join(r.text for r in p.runs).strip()
                if line:
                    parts.append(line)
        drafts.append("\n".join(parts))
    return drafts
