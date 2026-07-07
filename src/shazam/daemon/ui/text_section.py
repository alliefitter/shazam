from importlib.resources import files

from PIL.Image import Image
from PIL.ImageFont import FreeTypeFont, truetype

from shazam.daemon.ui.lib import draw_text_with_shadow, text_height
from shazam.lib.config import get_config

config = get_config()
SHARE = files("shazam.share")
TEXT_X = 660
HEADER_FONT = truetype(str(SHARE.joinpath("CourierPrime-Bold.ttf")), config.header_font_size)


class TextSection:
    def __init__(self, title: str, label: str, font: FreeTypeFont):
        self.title = title
        self.font = font
        self.label = label

    @property
    def label_height(self) -> int:
        return text_height(self.label, self.font)

    @property
    def title_height(self) -> int:
        return text_height(self.title, HEADER_FONT)

    @property
    def total_height(self) -> int:
        return self.title_height + self.label_height

    def draw_text(self, img: Image, title_y: int, label_y: int) -> Image:
        img = draw_text_with_shadow(
            img,
            self.title,
            (TEXT_X, title_y),
            HEADER_FONT,
            (0, 0, 0, 255),
            (140, 140, 140, 255),
            underline=True,
        )
        return draw_text_with_shadow(
            img,
            self.label,
            (TEXT_X, label_y),
            self.font,
            (200, 200, 200, 255),
            (0, 0, 0, 255),
        )
