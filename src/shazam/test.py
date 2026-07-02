from importlib.resources import files

from PIL.Image import Image
from PIL.Image import open as image_open
from PIL.ImageDraw import Draw
from PIL.ImageFont import FreeTypeFont, truetype

SHARE = files("shazam.share")
artist = "Neil Young"
title = "For the Turnstiles (2016 Remaster) slkjl ldkfjsl lkje klk kjelfjs lsej lkesjs"
album = "For the Turnstiles (2016 Remaster) alsdkjfsld elkjlj lkje l kj llkjlkj sdfjkelke lkejklej lke"
release_date = "2016-10-17"

background = image_open(str(SHARE.joinpath("grey_shadow_box.jpg")))
album_cover = image_open(str(SHARE.joinpath("on_the_beach.jpeg")))
background.paste(album_cover, (100, 90))
artist_font = truetype(str(SHARE.joinpath("CourierPrime-Regular.ttf")), 32)
other_font = truetype(str(SHARE.joinpath("CourierPrime-Regular.ttf")), 28)
title_font = truetype(str(SHARE.joinpath("CourierPrime-Bold.ttf")), 24)

TEXT_X = 420
COVER_TOP = 90
COVER_HEIGHT = 300
max_text_width = 800 - TEXT_X - 20

artist_wrapped = wrap_text(artist, artist_font, max_text_width)
title_wrapped = wrap_text(title, other_font, max_text_width)
album_wrapped = wrap_text(album, other_font, max_text_width)


total_text = (
    text_height("Artist", title_font)
    + text_height(artist_wrapped, artist_font)
    + text_height("Title", title_font)
    + text_height(title_wrapped, other_font)
    + text_height("Album", title_font)
    + text_height(album_wrapped, other_font)
)
# 3 label gaps + 2 section gaps; keep section gap = 2x label gap → 7 gaps total
LABEL_GAP = max(5, (COVER_HEIGHT - total_text) // 7)
SECTION_GAP = LABEL_GAP * 2

artist_label_y = COVER_TOP
artist_text_y = artist_label_y + text_height("Artist", title_font) + LABEL_GAP
title_label_y = artist_text_y + text_height(artist_wrapped, artist_font) + SECTION_GAP
title_text_y = title_label_y + text_height("Title", title_font) + LABEL_GAP
album_label_y = title_text_y + text_height(title_wrapped, other_font) + SECTION_GAP
album_text_y = album_label_y + text_height("Album", title_font) + LABEL_GAP


processed_image = draw_text_with_shadow(
    processed_image,
    "Title",
    (TEXT_X, title_label_y),
    title_font,
    (0, 0, 0, 255),
    (150, 150, 150, 255),
    underline=True,
)
processed_image = draw_text_with_shadow(
    processed_image,
    title_wrapped,
    (TEXT_X, title_text_y),
    other_font,
    (150, 150, 150, 255),
    (0, 0, 0, 255),
)
processed_image = draw_text_with_shadow(
    processed_image,
    "Album",
    (TEXT_X, album_label_y),
    title_font,
    (0, 0, 0, 255),
    (150, 150, 150, 255),
    underline=True,
)
processed_image = draw_text_with_shadow(
    processed_image,
    album_wrapped,
    (TEXT_X, album_text_y),
    other_font,
    (150, 150, 150, 255),
    (0, 0, 0, 255),
)
with open(SHARE.joinpath("test.jpg"), "wb") as f:
    processed_image.convert("RGB").save(f)
