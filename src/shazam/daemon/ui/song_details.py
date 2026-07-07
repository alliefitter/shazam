from importlib.resources import files

from PIL.Image import Image
from PIL.ImageFont import truetype

from shazam.daemon.song_lookup import SongInfo
from shazam.daemon.ui.lib import wrap_text
from shazam.daemon.ui.text_section import TextSection
from shazam.lib.config import get_config

config = get_config()
SHARE = files("shazam.share")
ALBUM_COVER_TOP = 100
SECTION_SPAN = 500
PREVIOUS_SONG_SPAN = 600
TITLE_FONT = truetype(str(SHARE.joinpath("CourierPrime-Regular.ttf")), config.title_font_size)
OTHER_FONT = truetype(str(SHARE.joinpath("CourierPrime-Regular.ttf")), config.other_font_size)
PREVIOUS_SONG_FONT = truetype(str(SHARE.joinpath("CourierPrime-Bold.ttf")), config.previous_song_font_size)


class SongDetails:
    def __init__(self, song: SongInfo, previous_song: SongInfo | None):
        self.artist = song.artist
        self.title = song.title
        self.album = song.album
        self.previous_song = previous_song

    def draw(self, img: Image) -> Image:
        span_height = SECTION_SPAN
        sections = [
            TextSection(*args)
            for args in (
                ("Title", wrap_text(self.title, TITLE_FONT), TITLE_FONT),
                ("Artist", wrap_text(self.artist, OTHER_FONT), OTHER_FONT),
                ("Album", wrap_text(self.album, OTHER_FONT), OTHER_FONT),
            )
        ]
        if self.previous_song:
            span_height = PREVIOUS_SONG_SPAN
            sections.append(
                TextSection(
                    "Previous Song",
                    self._make_previous_song_label(self.previous_song),
                    PREVIOUS_SONG_FONT,
                )
            )

        img = self._draw_sections(img, sections, ALBUM_COVER_TOP, span_height)

        return img

    def _draw_sections(
            self, img: Image, sections: list[TextSection], y: int, span_height: int
    ) -> Image:
        total_height = sum([s.total_height for s in sections])
        n = len(sections)
        available = max(0, span_height - total_height)
        title_gap = max(0, available // (n + 2 * (n - 1)))
        section_gap = title_gap * 2
        for i, section in enumerate(sections):
            title_y = y
            label_y = y + section.title_height + title_gap
            img = section.draw_text(img, title_y, label_y)
            y = label_y + section.label_height
            if i < len(sections) - 1:
                y += section_gap

        return img

    def _make_previous_song_label(self, previous_song: SongInfo) -> str:
        label = ""
        lines = [
            previous_song.title,
            previous_song.artist,
            previous_song.album,
        ]
        for line in lines:
            label += f"{wrap_text(line, PREVIOUS_SONG_FONT)}\n"

        return label
