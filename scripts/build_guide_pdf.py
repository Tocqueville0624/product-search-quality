#!/usr/bin/env python3
"""Build the local Chinese project guide from its maintained Markdown sources.

Run with the project's docs dependencies installed. Fonts stay on the host;
set SEARCH_QUALITY_PDF_FONT to a Unicode TrueType font on other machines.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
from pathlib import Path
from xml.sax.saxutils import quoteattr

from markdown_it import MarkdownIt
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
FONT_NAME = "GuideUnicode"
BLUE = colors.HexColor("#1c496a")
INK = colors.HexColor("#23313b")
MUTED = colors.HexColor("#657782")
RULE = colors.HexColor("#d6e1e7")
LIGHT = colors.HexColor("#f3f7fa")


def register_font(font_path: Path) -> None:
    if not font_path.is_file():
        raise FileNotFoundError(
            f"Unicode font not found: {font_path}. Set SEARCH_QUALITY_PDF_FONT "
            "to an installed Unicode TrueType font; fonts are not bundled."
        )
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(font_path)))
    # The host font has one face. Use size/colour/spacing for hierarchy instead
    # of claiming another installed Chinese font or silently losing its glyphs.
    pdfmetrics.registerFontFamily(
        FONT_NAME, normal=FONT_NAME, bold=FONT_NAME, italic=FONT_NAME, boldItalic=FONT_NAME
    )


def make_styles() -> dict[str, ParagraphStyle]:
    common = dict(fontName=FONT_NAME, textColor=INK, wordWrap="CJK", splitLongWords=True)
    body = ParagraphStyle(
        "GuideBody", fontSize=10, leading=16, spaceAfter=8, **common
    )
    return {
        "body": body,
        "title": ParagraphStyle(
            "GuideTitle", parent=body, fontSize=23, leading=32,
            textColor=BLUE, spaceAfter=17, keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "GuideChapter", parent=body, fontSize=17, leading=24,
            textColor=BLUE, spaceBefore=3, spaceAfter=13, keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "GuideSubhead", parent=body, fontSize=12, leading=18,
            textColor=BLUE, spaceBefore=10, spaceAfter=7, keepWithNext=True,
        ),
        "cell": ParagraphStyle(
            "GuideCell", parent=body, fontSize=8.8, leading=13.2,
            spaceAfter=0, alignment=TA_LEFT,
        ),
        "cell_header": ParagraphStyle(
            "GuideCellHeader", parent=body, fontSize=9, leading=13.3,
            textColor=BLUE, spaceAfter=0,
        ),
        "quote": ParagraphStyle(
            "GuideQuote", parent=body, leftIndent=12, rightIndent=8,
            textColor=BLUE, borderColor=RULE, borderWidth=0.8,
            borderPadding=9, backColor=LIGHT, spaceBefore=4, spaceAfter=12,
        ),
        "list": ParagraphStyle(
            "GuideList", parent=body, leftIndent=15, firstLineIndent=-12,
            spaceAfter=7,
        ),
        "code": ParagraphStyle(
            "GuideCode", fontName="Courier", fontSize=8.4, leading=12.5,
            textColor=INK, leftIndent=5, rightIndent=5, spaceAfter=0,
        ),
    }


def inline_xml(token) -> str:
    parts: list[str] = []
    for child in token.children or []:
        kind = child.type
        if kind == "text":
            parts.append(html.escape(child.content))
        elif kind in ("softbreak", "hardbreak"):
            parts.append("<br/>" if kind == "hardbreak" else " ")
        elif kind == "code_inline":
            parts.append(f'<font color="#29516b">{html.escape(child.content)}</font>')
        elif kind == "strong_open":
            parts.append('<font color="#173f5a">')
        elif kind == "strong_close":
            parts.append("</font>")
        elif kind == "em_open":
            parts.append("<i>")
        elif kind == "em_close":
            parts.append("</i>")
        elif kind == "link_open":
            href = child.attrGet("href") or ""
            if not href.startswith(("https://", "http://", "mailto:")):
                # Local Markdown links have no portable PDF URI. Keep their
                # readable labels; actual source paths remain in the guide.
                href = ""
            parts.append(f'<link href={quoteattr(href)} color="#176699">' if href else "<u>")
        elif kind == "link_close":
            # Find the nearest preceding open link without depending on global
            # state; Markdown inline links do not nest.
            prior = next(
                (p for p in reversed(parts) if p.startswith("<link ") or p == "<u>"), "<u>"
            )
            parts.append("</link>" if prior.startswith("<link ") else "</u>")
        elif kind == "image":
            parts.append(html.escape(child.content))
        elif kind == "html_inline":
            # Do not pass arbitrary source HTML through ReportLab's parser.
            if child.content.lower() in ("<br>", "<br/>", "<br />"):
                parts.append("<br/>")
    return "".join(parts)


class GuideDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str, **kwargs):
        super().__init__(filename, **kwargs)
        self.heading_number = 0

    def afterFlowable(self, flowable):
        level = getattr(flowable, "outline_level", None)
        if level is None:
            return
        label = flowable.getPlainText()
        self.heading_number += 1
        key = f"heading-{self.heading_number}"
        self.canv.bookmarkPage(key)
        # Single-level outline avoids illegal level jumps for appendix headings.
        self.canv.addOutlineEntry(label, key, level=0, closed=False)


def table_widths(rows: list[list[str]], width: float) -> list[float]:
    n = len(rows[0])
    if n == 2:
        weights = [0.29, 0.71]
    elif n == 3:
        weights = [0.29, 0.35, 0.36]
    elif n == 4:
        if "教学判断" in " ".join(rows[0]):
            weights = [0.22, 0.28, 0.10, 0.40]
        else:
            weights = [0.21, 0.23, 0.28, 0.28]
    else:
        weights = [1 / n] * n
    return [width * weight for weight in weights]


def markdown_flowables(source: str, styles: dict, width: float):
    parser = MarkdownIt("commonmark", {"html": True}).enable("table")
    tokens = parser.parse(source)
    result = []
    lists: list[dict] = []
    in_quote = False
    i = 0
    while i < len(tokens):
        token = tokens[i]
        kind = token.type
        if kind == "heading_open":
            level = int(token.tag[1:])
            style = styles["title" if level == 1 else "h2" if level == 2 else "h3"]
            paragraph = Paragraph(inline_xml(tokens[i + 1]), style)
            if level <= 2:
                paragraph.outline_level = level
            result.append(paragraph)
            i += 3
            continue
        if kind == "paragraph_open":
            content = inline_xml(tokens[i + 1])
            if lists:
                item = lists[-1]
                prefix = f'{item["next"]}.' if item["ordered"] else "•"
                content = html.escape(prefix) + " " + content
                item["next"] += 1
                style = styles["list"]
            else:
                style = styles["quote"] if in_quote else styles["body"]
            result.append(Paragraph(content, style))
            i += 3
            continue
        if kind in ("bullet_list_open", "ordered_list_open"):
            lists.append({"ordered": kind == "ordered_list_open", "next": int(token.attrGet("start") or 1)})
        elif kind in ("bullet_list_close", "ordered_list_close"):
            lists.pop()
        elif kind == "blockquote_open":
            in_quote = True
        elif kind == "blockquote_close":
            in_quote = False
        elif kind in ("fence", "code_block"):
            code = Preformatted(token.content.rstrip(), styles["code"], maxLineLength=83)
            table = Table([[code]], colWidths=[width], hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            result.extend([table, Spacer(1, 9)])
        elif kind == "table_open":
            rows = []
            row = []
            i += 1
            while i < len(tokens) and tokens[i].type != "table_close":
                current = tokens[i]
                if current.type == "tr_open":
                    row = []
                elif current.type == "inline":
                    row.append(inline_xml(current))
                elif current.type == "tr_close":
                    rows.append(row)
                i += 1
            data = [
                [Paragraph(cell, styles["cell_header" if ri == 0 else "cell"]) for cell in cells]
                for ri, cells in enumerate(rows)
            ]
            table = Table(
                data, colWidths=table_widths(rows, width), repeatRows=1,
                hAlign="LEFT", splitByRow=1, splitInRow=1,
            )
            table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9f1f6")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fb")]),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, RULE),
                ("LINEBELOW", (0, 1), (-1, -1), 0.35, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            result.extend([table, Spacer(1, 11)])
        elif kind == "html_block" and "pagebreak" in token.content:
            result.append(PageBreak())
        elif kind == "hr":
            result.append(Spacer(1, 9))
        i += 1
    return result


def page_decoration(canvas, doc):
    page_width, page_height = A4
    canvas.saveState()
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, page_height - 29, "Product Search Quality")
    canvas.drawRightString(page_width - doc.rightMargin, page_height - 29, "本地 PySpark · 技术学习手册")
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, page_height - 38, page_width - doc.rightMargin, page_height - 38)
    canvas.line(doc.leftMargin, 36, page_width - doc.rightMargin, 36)
    canvas.setFont(FONT_NAME, 7.5)
    canvas.drawString(doc.leftMargin, 23, "独立作品集项目 · 教学示例与实测结果分别标明")
    canvas.drawRightString(page_width - doc.rightMargin, 23, str(doc.page))
    canvas.restoreState()


def audit_and_render(pdf_path: Path, render_dir: Path) -> dict:
    import fitz

    render_dir.mkdir(parents=True, exist_ok=True)
    pdf = fitz.open(pdf_path)
    pages = []
    issues = []
    for index, page in enumerate(pdf):
        text = page.get_text()
        if not text.strip():
            issues.append({"page": index + 1, "issue": "no extractable text"})
        if "\ufffd" in text:
            issues.append({"page": index + 1, "issue": "replacement character"})
        bounds = []
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    x0, y0, x1, y1 = span["bbox"]
                    if x0 < -0.5 or y0 < -0.5 or x1 > page.rect.width + 0.5 or y1 > page.rect.height + 0.5:
                        bounds.append({"text": span["text"], "bbox": list(span["bbox"])})
        if bounds:
            issues.append({"page": index + 1, "issue": "text outside page", "spans": bounds})
        image_path = render_dir / f"page-{index + 1:02d}.png"
        page.get_pixmap(matrix=fitz.Matrix(1.25, 1.25), alpha=False).save(image_path)
        pages.append({"page": index + 1, "characters": len(text), "links": len(page.get_links()), "render": os.path.relpath(image_path, ROOT)})
    result = {
        "pdf": os.path.relpath(pdf_path, ROOT), "pages": len(pdf),
        "page_checks": pages, "issues": issues,
        "note": "Programmatic bounds/text checks supplement visual inspection; they do not prove visual quality.",
    }
    (render_dir / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    if issues:
        raise RuntimeError(f"PDF audit found {len(issues)} issues; see {render_dir / 'audit.json'}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/local/Product_Search_Quality_Technical_Guide_ZH.pdf")
    parser.add_argument("--font", type=Path, default=Path(os.environ.get("SEARCH_QUALITY_PDF_FONT", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf")))
    parser.add_argument("--skip-render", action="store_true", help="Build PDF without page images; default renders and audits every page.")
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    register_font(args.font)
    styles = make_styles()
    doc = GuideDocTemplate(
        str(output), pagesize=A4, leftMargin=46, rightMargin=46,
        topMargin=54, bottomMargin=50,
        title="Product Search Quality — 中文技术学习手册",
        author="Product Search Quality project", subject="Local PySpark, ML evaluation and operational review priorities",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="guide", frames=[frame], onPage=page_decoration))
    source = (ROOT / "docs/technical-guide.zh.md").read_text()
    resources = (ROOT / "docs/learning-resources.md").read_text()
    resources = re.sub(r"\A# .*", "# 附录：学习资料与练习目标", resources, count=1)
    story = markdown_flowables(source, styles, doc.width)
    story.append(PageBreak())
    story.extend(markdown_flowables(resources, styles, doc.width))
    doc.build(story)
    print(f"Generated {output}")
    if not args.skip_render:
        result = audit_and_render(output, output.parent / "guide-render")
        print(f"Rendered {result['pages']} pages; bounds/text audit passed.")


if __name__ == "__main__":
    main()
