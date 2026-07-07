from logging import getLogger

from PIL.Image import Image, new
from PIL.ImageDraw import Draw
from PIL.ImageFont import FreeTypeFont

logger = getLogger(__name__)

MAX_WIDTH = 600
_MEASURE = Draw(new("RGBA", (1280, 800)))


def wrap_text(text: str, font: FreeTypeFont):
    try:
        words = text.split()
        lines = []
        current = []
        for word in words:
            test = " ".join(current + [word])
            if font.getlength(test) <= MAX_WIDTH:
                current.append(word)
            else:
                if current:
                    lines.append(" ".join(current))
                current = [word]
        if current:
            lines.append(" ".join(current))
        return "\n".join(lines)
    except Exception as e:
        logger.error("Text wrap error", exc_info=e)
        return ""


def draw_text_with_shadow(
        img: Image,
        text: str,
        pos: tuple[int, int],
        font: FreeTypeFont,
        text_color: tuple[int, int, int, int],
        shadow_color: tuple[int, int, int, int],
        shadow_offset: tuple[int, int] = (2, -1),
        underline: bool = False,
) -> Image:
    x, y = pos
    ox, oy = shadow_offset
    img = img.convert("RGBA")
    draw = Draw(img)
    draw.text((x + ox, y + oy), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=text_color)
    if underline:
        bbox = draw.textbbox((x, y), text, font=font)
        draw.line(
            [(bbox[0], bbox[3] + 1), (bbox[2], bbox[3] + 1)], fill=text_color, width=1
        )
    return img


def text_height(text: str, font: FreeTypeFont) -> int:
    bbox = _MEASURE.textbbox((0, 0), text, font=font)
    return int(bbox[3] - bbox[1])
