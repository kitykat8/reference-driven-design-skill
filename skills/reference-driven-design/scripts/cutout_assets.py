#!/usr/bin/env python3
"""
Unified Icon Sheet Slicer & AI/Matting Background Cutout Engine (`cutout_assets.py`)
Part of the `reference-driven-design` skill.

Capabilities:
1. `--mode single`: Removes the background from a generated subject/illustration/object image:
   - Supports `--engine rembg` (neural salient-object segmentation via `rembg` + edge defringing)
   - Supports `--engine matting` (precision continuous alpha-matting + color decontamination for icons,
     vector graphics, studio renders, and objects on solid/uniform backgrounds)
   - Supports `--engine auto` (automatically picks `matting` for uniform-background icons/graphics
     and `rembg` for complex natural scenes if `rembg` is installed).
2. `--mode grid` (`--grid 2x2` or `3x3`): Slices a single AI-generated Unified Icon Sheet into
   individual icons, removes the background from every icon with zero halo, auto-trims and centers
   each icon in a uniform square PNG (`RGBA`), optionally generates recolored token variants
   (`--recolor "#EFE852,#FAFAFA,#0A0A0A"`), and produces a checkerboard verification sheet.
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def estimate_corner_bg_color(arr_rgb: np.ndarray, patch: int = 12) -> tuple[np.ndarray, float]:
    """Sample the 4 corners of an image to estimate background RGB and its uniformity (std)."""
    h, w, _ = arr_rgb.shape
    p = max(2, min(patch, h // 8, w // 8))
    corners = np.concatenate(
        [
            arr_rgb[:p, :p].reshape(-1, 3),
            arr_rgb[:p, -p:].reshape(-1, 3),
            arr_rgb[-p:, :p].reshape(-1, 3),
            arr_rgb[-p:, -p:].reshape(-1, 3),
        ],
        axis=0,
    ).astype(np.float32)
    bg_color = np.median(corners, axis=0)
    bg_std = float(np.mean(np.std(corners, axis=0)))
    return bg_color, bg_std


def remove_bg_matting(
    img: Image.Image,
    low_thresh: float = 22.0,
    high_thresh: float = 75.0,
    flood_connected_only: bool = False,
) -> Image.Image:
    """
    Precision continuous color-distance alpha matting + foreground color decontamination.
    Eliminates white/black halos around icons, line art, 3D objects, and studio cutouts.
    """
    rgba = img.convert("RGBA")
    arr = np.array(rgba, dtype=np.float32)
    rgb = arr[:, :, :3]
    bg_color, _ = estimate_corner_bg_color(rgb)

    # Euclidean distance in RGB space from background color
    diff = rgb - bg_color.reshape(1, 1, 3)
    dist = np.sqrt(np.sum(diff * diff, axis=2))

    # Continuous ramp for smooth anti-aliased edges
    alpha_norm = np.clip((dist - low_thresh) / max(1.0, (high_thresh - low_thresh)), 0.0, 1.0)

    if flood_connected_only:
        try:
            import cv2

            bg_mask = (dist < high_thresh).astype(np.uint8)
            h, w = bg_mask.shape
            flood = bg_mask.copy()
            mask = np.zeros((h + 2, w + 2), np.uint8)
            for seed in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
                if flood[seed[1], seed[0]] == 1:
                    cv2.floodFill(flood, mask, seed, 2)
            exterior_bg = flood == 2
            alpha_norm = np.where(exterior_bg, alpha_norm, 1.0)
        except Exception:
            pass

    # Foreground color decontamination on semi-transparent edge pixels:
    # Observed pixel C = alpha * C_fg + (1 - alpha) * C_bg  =>  C_fg = (C - (1 - alpha) * C_bg) / alpha
    safe_alpha = np.maximum(alpha_norm, 0.08)[:, :, None]
    decontam_rgb = (rgb - (1.0 - safe_alpha) * bg_color.reshape(1, 1, 3)) / safe_alpha
    decontam_rgb = np.clip(decontam_rgb, 0.0, 255.0)

    out = np.zeros_like(arr, dtype=np.uint8)
    out[:, :, :3] = decontam_rgb.astype(np.uint8)
    out[:, :, 3] = (alpha_norm * 255.0).astype(np.uint8)
    return Image.fromarray(out, mode="RGBA")


def remove_bg_rembg(img: Image.Image) -> Image.Image:
    """
    Neural salient-object background removal via `rembg` + border color decontamination
    so cutout subjects never have a bright/dark fringe on contrasting presentation slides.
    """
    from rembg import remove

    cutout = remove(img.convert("RGBA"))
    arr = np.array(cutout, dtype=np.float32)
    orig_rgb = np.array(img.convert("RGB"), dtype=np.float32)
    bg_color, bg_std = estimate_corner_bg_color(orig_rgb)

    alpha_norm = arr[:, :, 3] / 255.0
    # Soften 1px outer fringe and decontaminate edge colors if corners were uniform
    if bg_std < 35.0:
        safe_alpha = np.maximum(alpha_norm, 0.12)[:, :, None]
        edge_zone = (alpha_norm > 0.02) & (alpha_norm < 0.92)
        decontam = np.clip((arr[:, :, :3] - (1.0 - safe_alpha) * bg_color.reshape(1, 1, 3)) / safe_alpha, 0.0, 255.0)
        arr[:, :, :3] = np.where(edge_zone[:, :, None], decontam, arr[:, :, :3])

    out = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(out, mode="RGBA")


def remove_background(img: Image.Image, engine: str = "auto", flood_only: bool = False) -> Image.Image:
    rgb = np.array(img.convert("RGB"), dtype=np.float32)
    _, bg_std = estimate_corner_bg_color(rgb)

    if engine == "matting":
        return remove_bg_matting(img, flood_connected_only=flood_only)
    elif engine == "rembg":
        try:
            return remove_bg_rembg(img)
        except Exception as e:
            print(f"[WARN] rembg fallback to matting ({e})", file=sys.stderr)
            return remove_bg_matting(img, flood_connected_only=True)
    else:
        # auto mode: if corners are very uniform (solid studio/icon background) and flood_only is not set,
        # use rembg for natural photos if available, or matting for clean flat-background graphics
        if bg_std < 8.0 and not flood_only:
            try:
                # Check if image looks like a flat icon/graphic vs photo
                unique_colors = len(np.unique(rgb.reshape(-1, 3) // 16, axis=0))
                if unique_colors < 120:
                    return remove_bg_matting(img, flood_connected_only=False)
            except Exception:
                pass
        try:
            return remove_bg_rembg(img)
        except Exception:
            return remove_bg_matting(img, flood_connected_only=flood_only)


def trim_and_pad_square(img_rgba: Image.Image, canvas_size: int = 512, pad_ratio: float = 0.12) -> Image.Image:
    """Crop transparent margins around an icon/object and center it inside a uniform square RGBA canvas."""
    arr = np.array(img_rgba)
    alpha = arr[:, :, 3]
    ys, xs = np.where(alpha > 20)
    if len(xs) == 0 or len(ys) == 0:
        return img_rgba.resize((canvas_size, canvas_size), Image.Resampling.LANCZOS)

    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    cropped = img_rgba.crop((x0, y0, x1, y1))

    inner_max = int(canvas_size * (1.0 - 2.0 * pad_ratio))
    cw, ch = cropped.size
    scale = min(inner_max / max(1, cw), inner_max / max(1, ch))
    nw, nh = max(1, int(round(cw * scale))), max(1, int(round(ch * scale)))
    resized = cropped.resize((nw, nh), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    ox = (canvas_size - nw) // 2
    oy = (canvas_size - nh) // 2
    canvas.paste(resized, (ox, oy), resized)
    return canvas


def recolor_rgba(img_rgba: Image.Image, hex_color: str) -> Image.Image:
    """Recolor a cutout icon to an exact hex color token while preserving its smooth alpha channel."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    arr = np.array(img_rgba).copy()
    arr[:, :, 0] = r
    arr[:, :, 1] = g
    arr[:, :, 2] = b
    return Image.fromarray(arr, mode="RGBA")


def render_checkerboard(w: int, h: int, cell: int = 16) -> Image.Image:
    """Create a dark/mid-gray transparency checkerboard to verify cutout quality visually."""
    y_idx = np.arange(h) // cell
    x_idx = np.arange(w) // cell
    grid = (y_idx[:, None] + x_idx[None, :]) % 2
    c1 = np.array([28, 28, 28], dtype=np.uint8)
    c2 = np.array([48, 48, 48], dtype=np.uint8)
    rgb = np.where(grid[:, :, None] == 0, c1, c2)
    return Image.fromarray(rgb, mode="RGB")


def build_verification_sheet(items: list[tuple[str, Image.Image]], out_path: str) -> None:
    cols = min(4, max(1, len(items)))
    rows = (len(items) + cols - 1) // cols
    cell_w, cell_h = 360, 360
    pad = 24
    header_h = 56
    sheet_w = cols * cell_w + (cols + 1) * pad
    sheet_h = header_h + rows * (cell_h + 36) + (rows + 1) * pad

    sheet = Image.new("RGB", (sheet_w, sheet_h), (12, 12, 12))
    draw = ImageDraw.Draw(sheet)
    draw.text((pad, 18), f"TRANSPARENT CUTOUT VERIFICATION SHEET // {len(items)} ASSETS (CHECKERBOARD = ALPHA 0)", fill=(239, 232, 82))

    for idx, (label, im_rgba) in enumerate(items):
        r = idx // cols
        c = idx % cols
        x = pad + c * (cell_w + pad)
        y = header_h + pad + r * (cell_h + 36 + pad)

        checker = render_checkerboard(cell_w, cell_h, cell=18)
        thumb = im_rgba.copy()
        thumb.thumbnail((cell_w - 32, cell_h - 32), Image.Resampling.LANCZOS)
        tx = (cell_w - thumb.width) // 2
        ty = (cell_h - thumb.height) // 2
        checker.paste(thumb, (tx, ty), thumb)

        sheet.paste(checker, (x, y))
        draw.rectangle([x - 1, y - 1, x + cell_w, y + cell_h], outline=(239, 232, 82), width=1)
        draw.text((x + 4, y + cell_h + 8), label, fill=(240, 240, 240))

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    sheet.save(out_path, format="JPEG", quality=92)


def main():
    parser = argparse.ArgumentParser(description="Cut out backgrounds from generated images & slice unified icon sheets")
    parser.add_argument("--input", "-i", required=True, help="Input image path")
    parser.add_argument("--mode", choices=["single", "grid"], default="single", help="single image cutout or grid icon slicer")
    parser.add_argument("--grid", default="2x2", help="Grid dimensions RxC when --mode grid (e.g., 2x2, 3x3, 2x3)")
    parser.add_argument("--engine", choices=["auto", "matting", "rembg"], default="auto", help="Cutout engine")
    parser.add_argument("--output", "-o", help="Output PNG path (for --mode single) or output directory (for --mode grid)")
    parser.add_argument("--prefix", "-p", default="icon", help="Filename prefix for --mode grid")
    parser.add_argument("--recolor", help="Comma-separated hex colors to also export recolored icon variants (e.g. '#EFE852,#0A0A0A,#FAFAFA')")
    parser.add_argument("--trim", action="store_true", help="Trim transparent bounds and center in square canvas")
    parser.add_argument("--preview", help="Optional path to save checkerboard verification JPG")
    args = parser.parse_args()

    img = Image.open(args.input)
    preview_items: list[tuple[str, Image.Image]] = []

    if args.mode == "single":
        out_path = args.output or (os.path.splitext(args.input)[0] + "_cutout.png")
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        cutout = remove_background(img, engine=args.engine, flood_only=False)
        if args.trim:
            cutout = trim_and_pad_square(cutout, canvas_size=800, pad_ratio=0.06)
        cutout.save(out_path, format="PNG")
        print(f"[OK] Saved transparent RGBA cutout -> {out_path}")
        preview_items.append((os.path.basename(out_path), cutout))

        if args.recolor:
            base_no_ext = os.path.splitext(out_path)[0]
            for hex_col in [c.strip() for c in args.recolor.split(",") if c.strip()]:
                clean_hex = hex_col.lstrip("#").lower()
                recol_img = recolor_rgba(cutout, hex_col)
                recol_path = f"{base_no_ext}_{clean_hex}.png"
                recol_img.save(recol_path, format="PNG")
                print(f"[OK] Saved recolored cutout ({hex_col}) -> {recol_path}")

    else:
        rows_str, cols_str = args.grid.lower().split("x")
        rows, cols = int(rows_str), int(cols_str)
        out_dir = args.output or os.path.dirname(os.path.abspath(args.input))
        os.makedirs(out_dir, exist_ok=True)

        w, h = img.size
        cell_w = w / cols
        cell_h = h / rows
        # Crop slightly inside each cell (4% margin) to avoid any border artifacts
        inset_x = int(cell_w * 0.04)
        inset_y = int(cell_h * 0.04)

        idx = 1
        for r in range(rows):
            for c in range(cols):
                x0 = int(round(c * cell_w)) + inset_x
                y0 = int(round(r * cell_h)) + inset_y
                x1 = int(round((c + 1) * cell_w)) - inset_x
                y1 = int(round((r + 1) * cell_h)) - inset_y
                cell_img = img.crop((x0, y0, x1, y1))

                # Icons in a unified sheet use matting by default so interior holes in line icons are preserved
                eng = "matting" if args.engine == "auto" else args.engine
                cutout = remove_background(cell_img, engine=eng, flood_only=False)
                cutout = trim_and_pad_square(cutout, canvas_size=512, pad_ratio=0.12)

                out_file = os.path.join(out_dir, f"{args.prefix}_{idx}.png")
                cutout.save(out_file, format="PNG")
                print(f"[OK] Extracted & cut out icon #{idx} -> {out_file}")
                preview_items.append((f"{args.prefix}_{idx}.png", cutout))

                if args.recolor:
                    for hex_col in [hc.strip() for hc in args.recolor.split(",") if hc.strip()]:
                        clean_hex = hex_col.lstrip("#").lower()
                        recol_img = recolor_rgba(cutout, hex_col)
                        recol_path = os.path.join(out_dir, f"{args.prefix}_{idx}_{clean_hex}.png")
                        recol_img.save(recol_path, format="PNG")
                idx += 1

    if args.preview and preview_items:
        build_verification_sheet(preview_items, args.preview)
        print(f"[OK] Saved checkerboard cutout verification sheet -> {args.preview}")


if __name__ == "__main__":
    main()
