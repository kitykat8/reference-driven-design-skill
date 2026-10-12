#!/usr/bin/env python3
"""
Fetch real visual design references (Behance, Pinterest, Dribbble, BP&O, Fonts In Use, Awwwards)
AND generate real TrueType (.ttf) visual Font Pairing Specimen Cards with Cyrillic & Latin support.

Outputs in <out_dir>:
1. <prefix>_1.jpg .. <prefix>_N.jpg — Individual downloaded visual reference images
2. <prefix>_moodboard.jpg — Stitched 2x2 visual moodboard of references
3. <prefix>_font_1.jpg .. <prefix>_font_3.jpg & <prefix>_fonts_sheet.jpg — Visual font pairing specimen cards
4. <prefix>_widget.html — Self-contained inline HTML widget (<agent-embed>) showing BOTH references and font pairings
5. <prefix>_manifest.json — Complete metadata

Usage:
  python fetch_references.py \
    -q "behance.net editorial presentation design layout" \
    -q "pinterest.com magazine presentation slide layout" \
    --sample-title "FELIS CATUS // МИР КОШЕК" \
    --sample-sub "Атлас пород, генетики и грации: 10 редакционных слайдов" \
    --font-presets "editorial,literary,avantgarde" \
    -o "C:/path/to/artifact_dir" -c 4 -p "cats_deck"
"""

import argparse
import base64
import html
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from typing import List, Dict, Any, Optional

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

AUTHENTIC_DOMAINS = (
    "behance.net",
    "pinimg.com",
    "pinterest.",
    "dribbble.com",
    "bpando.org",
    "fontsinuse.com",
    "awwwards.com",
    "pentagram.com",
    "logobook.com",
    "are.na",
    "cosmos.so",
    "mindsparklemag.com",
    "spinemagazine.co",
    "typewolf.com",
)

# Curated Font Pairings (all 100% available on Google Fonts with Cyrillic & Latin support)
FONT_PRESETS: Dict[str, Dict[str, str]] = {
    "editorial": {
        "id": "FONT #A",
        "name": "Editorial High-Contrast (Cormorant Garamond + Manrope + JetBrains Mono)",
        "vibe": "Журнальная эстетика Kinfolk / Vogue / Taschen: утонченная антиква + чистый гротеск",
        "display_family": "Cormorant Garamond",
        "display_weight": "700",
        "body_family": "Manrope",
        "body_weight": "400",
        "mono_family": "JetBrains Mono",
        "mono_weight": "500",
        "bg": "#F6F3EC",
        "ink": "#181715",
        "accent": "#B84A27",
        "google_css": "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,600;0,700;1,600&family=JetBrains+Mono:wght@400;500&family=Manrope:wght@400;500;600&display=swap",
    },
    "literary": {
        "id": "FONT #B",
        "name": "Natural History Atlas (Playfair Display + Golos Text + IBM Plex Mono)",
        "vibe": "Энциклопедический стиль National Geographic / Penguin Classics: выразительные засечки + швейцарский текст",
        "display_family": "Playfair Display",
        "display_weight": "700",
        "body_family": "Golos Text",
        "body_weight": "400",
        "mono_family": "IBM Plex Mono",
        "mono_weight": "500",
        "bg": "#141615",
        "ink": "#F2EFE9",
        "accent": "#D99B26",
        "google_css": "https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Playfair+Display:ital,wght@0,700;1,600&display=swap",
    },
    "avantgarde": {
        "id": "FONT #C",
        "name": "Modern Avant-Garde (Unbounded + Onest + JetBrains Mono)",
        "vibe": "Смелый фестивальный и Awwwards-стиль: широкий геометрический гротеск + минималистичная верстка",
        "display_family": "Unbounded",
        "display_weight": "700",
        "body_family": "Onest",
        "body_weight": "400",
        "mono_family": "JetBrains Mono",
        "mono_weight": "500",
        "bg": "#EAE6DF",
        "ink": "#121211",
        "accent": "#FF3E00",
        "google_css": "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Onest:wght@400;500;600&family=Unbounded:wght@600;700;800&display=swap",
    },
    "sculptural": {
        "id": "FONT #D",
        "name": "Gallery & Luxury Minimal (Forum + Plus Jakarta Sans + Space Mono)",
        "vibe": "Музейный каталог / Aesop / Architectural Digest: классические римские пропорции и воздух",
        "display_family": "Forum",
        "display_weight": "400",
        "body_family": "Manrope",
        "body_weight": "400",
        "mono_family": "Space Mono",
        "mono_weight": "400",
        "bg": "#EFECE6",
        "ink": "#1C1B19",
        "accent": "#3D5A45",
        "google_css": "https://fonts.googleapis.com/css2?family=Forum&family=Manrope:wght@400;500&family=Space+Mono&display=swap",
    },
    "swiss": {
        "id": "FONT #E",
        "name": "Swiss Neo-Brutalist Grid (Oswald + Inter + IBM Plex Mono)",
        "vibe": "Швейцарский плакатный стиль Йозефа Мюллера-Брокманна: плотный высокий гротеск и строгая сетка",
        "display_family": "Oswald",
        "display_weight": "700",
        "body_family": "Inter",
        "body_weight": "400",
        "mono_family": "IBM Plex Mono",
        "mono_weight": "500",
        "bg": "#F4F1EA",
        "ink": "#111111",
        "accent": "#E03C1F",
        "google_css": "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600&family=Oswald:wght@600;700&display=swap",
    },
}


def fetch_google_font_ttf(family: str, weight: str = "400") -> Optional[bytes]:
    """Download raw TrueType (.ttf) font bytes from Google Fonts CSS API using legacy User-Agent."""
    fam_Param = urllib.parse.quote_plus(f"{family}:{weight}")
    url = f"https://fonts.googleapis.com/css?family={fam_Param}&subset=cyrillic,latin"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/4.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            css = resp.read().decode("utf-8", errors="ignore")
        m = re.search(r"url\((https://[^)]+\.ttf)\)", css)
        if not m:
            return None
        ttf_url = m.group(1)
        with urllib.request.urlopen(ttf_url, timeout=8) as ttf_resp:
            return ttf_resp.read()
    except Exception as e:
        print(f"[WARN] Could not download font {family}:{weight}: {e}")
        return None


def load_pil_font(ttf_bytes: Optional[bytes], size: int) -> Any:
    if ttf_bytes and HAS_PIL:
        try:
            return ImageFont.truetype(io.BytesIO(ttf_bytes), size)
        except Exception:
            pass
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def render_font_specimen_cards(
    preset_keys: List[str],
    sample_title: str,
    sample_sub: str,
    out_dir: str,
    prefix: str,
) -> List[Dict[str, Any]]:
    """Render visual specimen cards for each selected font pairing."""
    if not HAS_PIL:
        return []

    rendered_fonts: List[Dict[str, Any]] = []
    card_w, card_h = 820, 310

    for idx, key in enumerate(preset_keys):
        spec = FONT_PRESETS.get(key)
        if not spec:
            continue

        disp_bytes = fetch_google_font_ttf(spec["display_family"], spec["display_weight"])
        body_bytes = fetch_google_font_ttf(spec["body_family"], spec["body_weight"])
        mono_bytes = fetch_google_font_ttf(spec["mono_family"], spec["mono_weight"])

        f_disp = load_pil_font(disp_bytes, 44)
        f_body = load_pil_font(body_bytes, 17)
        f_mono = load_pil_font(mono_bytes, 13)
        f_badge = load_pil_font(mono_bytes, 14)

        bg_rgb = hex_to_rgb(spec["bg"])
        ink_rgb = hex_to_rgb(spec["ink"])
        acc_rgb = hex_to_rgb(spec["accent"])

        card = Image.new("RGB", (card_w, card_h), bg_rgb)
        draw = ImageDraw.Draw(card)

        # Auto-fit display font size if wide typeface (like Unbounded) exceeds card width
        disp_size = 44
        while disp_size > 24 and draw.textlength(sample_title[:36], font=f_disp) > (card_w - 56):
            disp_size -= 2
            f_disp = load_pil_font(disp_bytes, disp_size)

        # Top technical bar
        draw.rectangle([0, 0, card_w - 1, card_h - 1], outline=ink_rgb, width=2)
        draw.line([0, 46, card_w, 46], fill=ink_rgb, width=1)
        draw.rectangle([0, 0, 120, 46], fill=acc_rgb)
        draw.text((16, 14), spec["id"], fill=(255, 255, 255), font=f_badge)
        draw.text((136, 15), spec["name"], fill=ink_rgb, font=f_mono)

        # Sample Display Headline
        draw.text((28, 68), sample_title[:36], fill=ink_rgb, font=f_disp)

        # Sample Body copy
        draw.text((28, 134), sample_sub[:68], fill=ink_rgb, font=f_body)
        draw.text(
            (28, 164),
            f"Стиль: {spec['vibe'][:66]}",
            fill=acc_rgb,
            font=f_body,
        )

        # Bottom Font Stack Breakdown Bar
        draw.line([0, 224, card_w, 224], fill=ink_rgb, width=1)
        col_w = card_w // 3
        draw.line([col_w, 224, col_w, card_h], fill=ink_rgb, width=1)
        draw.line([col_w * 2, 224, col_w * 2, card_h], fill=ink_rgb, width=1)

        draw.text((18, 236), "ЗАГОЛОВКИ (DISPLAY):", fill=acc_rgb, font=f_mono)
        draw.text((18, 258), f"{spec['display_family']} ({spec['display_weight']})", fill=ink_rgb, font=f_body)

        draw.text((col_w + 18, 236), "ОСНОВНОЙ ТЕКСТ (BODY):", fill=acc_rgb, font=f_mono)
        draw.text((col_w + 18, 258), f"{spec['body_family']} ({spec['body_weight']})", fill=ink_rgb, font=f_body)

        draw.text((col_w * 2 + 18, 236), "ИНДЕКСЫ И ЦИФРЫ (MONO):", fill=acc_rgb, font=f_mono)
        draw.text((col_w * 2 + 18, 258), f"{spec['mono_family']}", fill=ink_rgb, font=f_mono)

        card_filename = f"{prefix}_font_{idx + 1}.jpg"
        card_path = os.path.join(out_dir, card_filename).replace("\\", "/")
        card.save(card_path, format="JPEG", quality=92)

        buf = io.BytesIO()
        card.resize((640, int(640 * card_h / card_w)), Image.Resampling.LANCZOS).save(buf, format="JPEG", quality=86)
        b64_card = base64.b64encode(buf.getvalue()).decode("ascii")

        rendered_fonts.append(
            {
                "id": spec["id"],
                "key": key,
                "name": spec["name"],
                "vibe": spec["vibe"],
                "display_family": spec["display_family"],
                "body_family": spec["body_family"],
                "mono_family": spec["mono_family"],
                "google_css": spec["google_css"],
                "local_path": card_path,
                "base64": b64_card,
            }
        )

    # Also stitch a single combined font sheet image
    if rendered_fonts:
        pad = 20
        sheet_w = card_w + pad * 2
        sheet_h = len(rendered_fonts) * (card_h + pad) + pad
        sheet = Image.new("RGB", (sheet_w, sheet_h), (234, 230, 223))
        for i, rf in enumerate(rendered_fonts):
            c_img = Image.open(rf["local_path"])
            sheet.paste(c_img, (pad, pad + i * (card_h + pad)))
        sheet_path = os.path.join(out_dir, f"{prefix}_fonts_sheet.jpg").replace("\\", "/")
        sheet.save(sheet_path, format="JPEG", quality=90)

    return rendered_fonts


def normalize_query(q: str) -> str:
    return re.sub(r"\bsite:([a-zA-Z0-9.-]+)", r"\1", q).strip()


def search_bing_images_async(query: str, max_results: int = 12) -> List[Dict[str, str]]:
    clean_q = normalize_query(query)
    encoded = urllib.parse.quote_plus(clean_q)
    url = f"https://www.bing.com/images/async?q={encoded}&first=0&count=25&mmasync=1"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,*/*",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
            "Referer": "https://www.bing.com/images/search",
        },
    )
    results: List[Dict[str, str]] = []
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            page_html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[WARN] Search request failed for '{clean_q}': {e}")
        return results

    matches = re.findall(r'm="(\{[^"]+murl[^"]+\})"', page_html)
    for raw in matches:
        try:
            unescaped = html.unescape(raw)
            data = json.loads(unescaped)
            murl = data.get("murl", "")
            turl = data.get("turl", "")
            purl = data.get("purl", "")
            title = data.get("t") or data.get("pt") or data.get("desc") or clean_q
            title = re.sub(r"<[^>]+>", "", title).strip()
            if murl or turl:
                results.append(
                    {
                        "query": clean_q,
                        "title": title,
                        "murl": murl,
                        "turl": turl,
                        "purl": purl,
                    }
                )
                if len(results) >= max_results:
                    break
        except Exception:
            continue

    return results


def download_image_bytes(murl: str, turl: str) -> bytes:
    for candidate in [murl, turl]:
        if not candidate:
            continue
        try:
            req = urllib.request.Request(
                candidate,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                    "Referer": "https://www.bing.com/",
                },
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()
                if len(data) > 3000:
                    return data
        except Exception:
            continue
    return b""


def normalize_to_jpeg(raw_bytes: bytes, max_dim: int = 900) -> bytes:
    if not HAS_PIL:
        return raw_bytes
    img = Image.open(io.BytesIO(raw_bytes))
    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (245, 243, 239))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if len(img.split()) > 3 else None)
        img = bg
    else:
        img = img.convert("RGB")

    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / float(max(w, h))
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88)
    return out.getvalue()


def is_authentic_design_source(purl: str, murl: str) -> bool:
    combined = ((purl or "") + " " + (murl or "")).lower()
    return any(dom in combined for dom in AUTHENTIC_DOMAINS)


def detect_platform_label(purl: str, murl: str, query: str) -> str:
    combined = ((purl or "") + " " + (murl or "") + " " + (query or "")).lower()
    if "behance." in combined:
        return "Behance"
    if "pinterest." in combined or "pinimg." in combined:
        return "Pinterest"
    if "awwwards." in combined:
        return "Awwwards"
    if "bpando." in combined:
        return "BP&O"
    if "fontsinuse." in combined:
        return "Fonts In Use"
    if "dribbble." in combined:
        return "Dribbble"
    return "Design Ref"


def create_moodboard_sheet(items: List[Dict[str, Any]], out_path: str) -> None:
    if not HAS_PIL or not items:
        return

    cols = min(len(items), 2) if len(items) <= 4 else 3
    rows = (len(items) + cols - 1) // cols
    cell_w, cell_h = 600, 450
    pad = 24
    header_h = 60
    board_w = cols * cell_w + (cols + 1) * pad
    board_h = header_h + rows * cell_h + (rows + 1) * pad

    board = Image.new("RGB", (board_w, board_h), (236, 232, 225))
    draw = ImageDraw.Draw(board)

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 20)
        font_sub = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    draw.text(
        (pad, 20),
        "SELECTED DESIGN REFERENCES // ВИЗУАЛЬНЫЕ РЕФЕРЕНСЫ",
        fill=(20, 20, 19),
        font=font_title,
    )

    for idx, item in enumerate(items):
        r = idx // cols
        c = idx % cols
        x0 = pad + c * (cell_w + pad)
        y0 = header_h + pad + r * (cell_h + pad)

        draw.rectangle([x0, y0, x0 + cell_w, y0 + cell_h], fill=(252, 250, 247), outline=(20, 20, 19), width=2)

        img_box_h = cell_h - 68
        try:
            img = Image.open(item["local_path"]).convert("RGB")
            iw, ih = img.size
            scale = min((cell_w - 16) / iw, (img_box_h - 16) / ih)
            nw, nh = int(iw * scale), int(ih * scale)
            img_resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
            px = x0 + (cell_w - nw) // 2
            py = y0 + 8 + (img_box_h - 16 - nh) // 2
            board.paste(img_resized, (px, py))
        except Exception:
            pass

        fy = y0 + img_box_h
        draw.line([x0, fy, x0 + cell_w, fy], fill=(20, 20, 19), width=1)
        badge_text = f"REF #{idx + 1} · {item['platform']}"
        draw.text((x0 + 14, fy + 10), badge_text, fill=(224, 60, 31), font=font_title)
        short_title = item["title"][:62] + ("..." if len(item["title"]) > 62 else "")
        draw.text((x0 + 14, fy + 38), short_title, fill=(40, 40, 38), font=font_sub)

    board.save(out_path, format="JPEG", quality=90)


def build_widget_html_string(items: List[Dict[str, Any]], font_items: List[Dict[str, Any]]) -> str:
    """Build interactive tabbed widget (<470px height) with Tab 1: Visual References & Tab 2: Font Pairings."""
    ref_cards = []
    for idx, item in enumerate(items):
        b64 = item["base64"]
        title_esc = html.escape(item["title"][:68])
        platform_esc = html.escape(item["platform"])
        purl_esc = html.escape(item["purl"] or "#")
        ref_cards.append(
            f"""
            <div class="border border-[var(--border)] bg-[var(--background)] rounded-lg overflow-hidden flex flex-col">
              <div class="relative bg-black/5 flex items-center justify-center" style="height: 185px; overflow: hidden;">
                <img src="data:image/jpeg;base64,{b64}" alt="{title_esc}" style="width: 100%; height: 100%; object-fit: cover;" />
                <span class="absolute top-2 left-2 px-2 py-0.5 text-xs font-semibold rounded bg-black/80 text-white">
                  Ref #{idx + 1} · {platform_esc}
                </span>
              </div>
              <div class="p-2.5 flex flex-col justify-between flex-1">
                <div class="text-xs font-medium text-[var(--foreground)] leading-snug line-clamp-2">{title_esc}</div>
                <a href="{purl_esc}" target="_blank" class="text-xs text-[var(--primary)] hover:underline mt-1 inline-block truncate">
                  Источник ({platform_esc}) ↗
                </a>
              </div>
            </div>
            """
        )

    font_cards = []
    for fitem in font_items:
        fb64 = fitem["base64"]
        fname = html.escape(fitem["name"])
        font_cards.append(
            f"""
            <div class="border border-[var(--border)] bg-[var(--background)] rounded-lg overflow-hidden">
              <img src="data:image/jpeg;base64,{fb64}" alt="{fname}" style="width: 100%; height: auto; display: block;" />
            </div>
            """
        )

    cols_class = "grid-cols-2 md:grid-cols-4" if len(items) >= 4 else f"grid-cols-{min(len(items), 3)}"
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
</head>
<body class="bg-transparent text-[var(--foreground)] antialiased p-2">
  <div class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-xl p-4 shadow-sm">
    <div class="flex items-center justify-between mb-3 gap-2 flex-wrap">
      <div>
        <h2 class="text-[var(--foreground)] font-semibold text-base">Референсы и Шрифтовые пары</h2>
        <p class="text-[var(--muted-foreground)] text-xs">Переключай вкладки, чтобы посмотреть референсы и подобранные шрифты</p>
      </div>
      <div class="flex gap-1.5">
        <button id="btnRefs" onclick="showTab('refs')" class="text-xs px-3 py-1.5 rounded-lg font-medium bg-[var(--primary)] text-[var(--primary-foreground)]">
          1. Визуальные референсы ({len(items)})
        </button>
        <button id="btnFonts" onclick="showTab('fonts')" class="text-xs px-3 py-1.5 rounded-lg font-medium border border-[var(--border)] text-[var(--foreground)]">
          2. Шрифтовые пары ({len(font_items)})
        </button>
      </div>
    </div>

    <div id="tabRefs" class="grid {cols_class} gap-3">
      {''.join(ref_cards)}
    </div>

    <div id="tabFonts" class="hidden grid grid-cols-1 md:grid-cols-3 gap-3">
      {''.join(font_cards)}
    </div>
  </div>

  <script>
    function showTab(tab) {{
      const r = document.getElementById('tabRefs');
      const f = document.getElementById('tabFonts');
      const br = document.getElementById('btnRefs');
      const bf = document.getElementById('btnFonts');
      if (tab === 'refs') {{
        r.classList.remove('hidden');
        f.classList.add('hidden');
        br.className = 'text-xs px-3 py-1.5 rounded-lg font-medium bg-[var(--primary)] text-[var(--primary-foreground)]';
        bf.className = 'text-xs px-3 py-1.5 rounded-lg font-medium border border-[var(--border)] text-[var(--foreground)]';
      }} else {{
        r.classList.add('hidden');
        f.classList.remove('hidden');
        bf.className = 'text-xs px-3 py-1.5 rounded-lg font-medium bg-[var(--primary)] text-[var(--primary-foreground)]';
        br.className = 'text-xs px-3 py-1.5 rounded-lg font-medium border border-[var(--border)] text-[var(--foreground)]';
      }}
    }}
  </script>
</body>
</html>
"""


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Fetch real visual design references + curated font pairings.")
    parser.add_argument("--query", "-q", action="append", required=True, help="Search query (can be passed multiple times)")
    parser.add_argument("--out-dir", "-o", required=True, help="Target artifact directory to save images and widget")
    parser.add_argument("--count", "-c", type=int, default=4, help="Total number of reference images to fetch (default: 4)")
    parser.add_argument("--prefix", "-p", default="ref", help="Filename prefix for saved files")
    parser.add_argument("--sample-title", default="АРХИТЕКТУРА ФОРМЫ // 2026", help="Sample headline text for font specimen cards")
    parser.add_argument("--sample-sub", default="Визуальная система, типографика и композиционная сетка проекта", help="Sample subtitle text for font specimen cards")
    parser.add_argument("--font-presets", default="editorial,literary,avantgarde", help="Comma-separated font preset keys: editorial,literary,avantgarde,sculptural,swiss")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    query_buckets: List[List[Dict[str, str]]] = []
    for q in args.query:
        query_buckets.append(search_bing_images_async(q, max_results=12))

    interleaved: List[Dict[str, str]] = []
    max_len = max((len(b) for b in query_buckets), default=0)
    for i in range(max_len):
        for b in query_buckets:
            if i < len(b):
                interleaved.append(b[i])

    authentic = [c for c in interleaved if is_authentic_design_source(c["purl"], c["murl"])]
    fallback = [c for c in interleaved if not is_authentic_design_source(c["purl"], c["murl"])]
    ordered_candidates = authentic + fallback

    seen_images = set()
    seen_pages = set()
    saved_items: List[Dict[str, Any]] = []

    for cand in ordered_candidates:
        img_key = cand["murl"] or cand["turl"]
        page_key = cand["purl"] or img_key
        if not img_key or img_key in seen_images or page_key in seen_pages:
            continue

        raw = download_image_bytes(cand["murl"], cand["turl"])
        if not raw:
            continue

        try:
            jpg_bytes = normalize_to_jpeg(raw)
        except Exception:
            continue

        seen_images.add(img_key)
        seen_pages.add(page_key)

        idx = len(saved_items) + 1
        filename = f"{args.prefix}_{idx}.jpg"
        local_path = os.path.join(args.out_dir, filename)
        with open(local_path, "wb") as f:
            f.write(jpg_bytes)

        thumb_bytes = normalize_to_jpeg(raw, max_dim=480)
        b64_str = base64.b64encode(thumb_bytes).decode("ascii")
        platform = detect_platform_label(cand["purl"], cand["murl"], cand["query"])

        saved_items.append(
            {
                "index": idx,
                "title": cand["title"],
                "platform": platform,
                "purl": cand["purl"],
                "image_url": cand["murl"] or cand["turl"],
                "local_path": local_path.replace("\\", "/"),
                "base64": b64_str,
            }
        )

        if len(saved_items) >= args.count:
            break

    moodboard_path = os.path.join(args.out_dir, f"{args.prefix}_moodboard.jpg").replace("\\", "/")
    if saved_items:
        create_moodboard_sheet(saved_items, moodboard_path)

    preset_keys = [k.strip() for k in args.font_presets.split(",") if k.strip()]
    font_items = render_font_specimen_cards(
        preset_keys=preset_keys,
        sample_title=args.sample_title,
        sample_sub=args.sample_sub,
        out_dir=args.out_dir,
        prefix=args.prefix,
    )

    widget_html_path = os.path.join(args.out_dir, f"{args.prefix}_widget.html").replace("\\", "/")
    if saved_items:
        with open(widget_html_path, "w", encoding="utf-8") as f:
            f.write(build_widget_html_string(saved_items, font_items))

    manifest_path = os.path.join(args.out_dir, f"{args.prefix}_manifest.json").replace("\\", "/")
    manifest_data = {
        "count": len(saved_items),
        "moodboard_path": moodboard_path,
        "fonts_sheet_path": os.path.join(args.out_dir, f"{args.prefix}_fonts_sheet.jpg").replace("\\", "/"),
        "widget_path": widget_html_path,
        "references": [{k: v for k, v in item.items() if k != "base64"} for item in saved_items],
        "font_pairings": [{k: v for k, v in fitem.items() if k != "base64"} for fitem in font_items],
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)

    print(json.dumps(manifest_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
