import io
import base64
from typing import Tuple, List, Optional, Any, Dict
from PIL import Image, ImageDraw, ImageFont

def decode_base64_image(image_data: str) -> Image.Image:
    """
    Decodes a base64 Data URL or raw base64 string into a Pillow RGB/RGBA image.
    """
    if not image_data:
        raise ValueError("Empty image data provided.")
    raw_b64 = image_data.split(",", 1)[1] if "," in image_data else image_data
    img_bytes = base64.b64decode(raw_b64)
    img = Image.open(io.BytesIO(img_bytes))
    return img

def get_image_display_dimensions(
    orig_w: float,
    orig_h: float,
    max_w: float,
    max_h: float
) -> Tuple[float, float]:
    """
    Computes scaled width and height that fit within max_w and max_h
    while strictly preserving the original aspect ratio.
    """
    if orig_w <= 0 or orig_h <= 0:
        return max_w, max_h
    scale = min(max_w / orig_w, max_h / orig_h, 1.0)
    return round(orig_w * scale, 2), round(orig_h * scale, 2)

def render_diagram_with_markers(
    image_data: str,
    diagram_mode: str,
    markers: List[Any]
) -> Tuple[bytes, float, float]:
    """
    Renders diagram markers onto the diagram image based on diagram_mode:
    1. 'numbered_markers': Draws circular numbered badges with high-contrast borders
       at the specified normalized (x, y) coordinates.
    2. 'blank_lines': Draws pin markers and callout leader lines with write-in blanks.

    Returns:
        (image_png_bytes, orig_width, orig_height)
    """
    img = decode_base64_image(image_data).convert("RGBA")
    w, h = img.size

    # Create overlay for crisp antialiased vector drawing
    overlay = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Dynamic badge radius scaled to image resolution
    base_radius = max(13, int(min(w, h) * 0.024))
    font_size = max(11, int(base_radius * 1.15))

    try:
        # Try loading standard scalable font, fallback to default
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

    for idx, marker in enumerate(markers, 1):
        m_x = float(getattr(marker, "x", marker.get("x", 0.0) if isinstance(marker, dict) else 0.0))
        m_y = float(getattr(marker, "y", marker.get("y", 0.0) if isinstance(marker, dict) else 0.0))
        m_num = getattr(marker, "number", marker.get("number", idx) if isinstance(marker, dict) else idx)

        # Normalized coordinates to actual image pixel coordinates
        px = max(base_radius + 2, min(int(m_x * w), w - base_radius - 2))
        py = max(base_radius + 2, min(int(m_y * h), h - base_radius - 2))

        num_str = str(m_num)

        if diagram_mode == "blank_lines":
            # Mode 2: Pointer marker dot + leader line to a blank label line
            dot_r = max(5, int(base_radius * 0.35))
            # Draw pointer center dot (vivid indigo/blue)
            draw.ellipse([px - dot_r, py - dot_r, px + dot_r, py + dot_r], fill=(67, 56, 202, 255), outline=(255, 255, 255, 255), width=2)

            # Determine leader direction (right if in left half, left if in right half)
            go_right = px < (w * 0.55)
            lead_len = int(min(w, h) * 0.12)
            end_x = min(w - 10, px + lead_len) if go_right else max(10, px - lead_len)
            end_y = py

            # Draw leader line
            draw.line([(px, py), (end_x, end_y)], fill=(30, 41, 59, 255), width=2)

            # Draw label line e.g. "1. __________________"
            lbl_line_len = int(min(w, h) * 0.18)
            line_start_x = end_x + 4 if go_right else max(10, end_x - lbl_line_len - 4)
            line_end_x = min(w - 6, line_start_x + lbl_line_len)
            draw.line([(line_start_x, end_y + 6), (line_end_x, end_y + 6)], fill=(15, 23, 42, 255), width=2)

            # Draw question number label
            draw.text((line_start_x - 14 if go_right else line_start_x, end_y - 10), f"({num_str})", fill=(15, 23, 42, 255), font=font)
        else:
            # Mode 1: Crisp numbered circular badge
            # Drop shadow
            draw.ellipse(
                [px - base_radius + 1, py - base_radius + 2, px + base_radius + 1, py + base_radius + 2],
                fill=(0, 0, 0, 80)
            )
            # Outer dark border
            draw.ellipse(
                [px - base_radius - 2, py - base_radius - 2, px + base_radius + 2, py + base_radius + 2],
                fill=(30, 41, 59, 255)
            )
            # Inner white circle
            draw.ellipse(
                [px - base_radius, py - base_radius, px + base_radius, py + base_radius],
                fill=(255, 255, 255, 255)
            )
            # Centered bold number
            bbox = font.getbbox(num_str) if hasattr(font, "getbbox") else (0, 0, 8, 12)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            text_x = px - (text_w / 2.0)
            text_y = py - (text_h / 2.0) - (bbox[1] if hasattr(font, "getbbox") else 0)
            draw.text((text_x, text_y), num_str, fill=(15, 23, 42, 255), font=font)

    # Composite overlay onto original image
    final_img = Image.alpha_composite(img, overlay).convert("RGB")
    buf = io.BytesIO()
    final_img.save(buf, format="PNG", quality=95)
    return buf.getvalue(), float(w), float(h)
