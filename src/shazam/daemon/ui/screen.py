from importlib.resources import files
from io import BytesIO
from logging import getLogger
from tkinter import Label, Tk

from PIL.Image import Image
from PIL.Image import open as image_open
from PIL.ImageTk import PhotoImage
from Xlib.display import Display
from Xlib.ext.dpms import DPMSModeOff, DPMSModeOn

from shazam.daemon.song_lookup import SongInfo
from shazam.daemon.ui.song_details import SongDetails

SHARE = files("shazam.share")

logger = getLogger(__name__)


class Screen:
    def __init__(self):
        self.root = Tk()
        self.root.config(cursor="none")
        self.root.attributes("-fullscreen", True)
        self.panel = Label(self.root, bg="#949494")
        self.display = Display()
        self.reset()
        self._is_blanked = False
        logger.info("Screen started")

    @property
    def is_blanked(self) -> bool:
        return self._is_blanked

    def blank(self):
        self.display.dpms_force_level(DPMSModeOff)
        self.display.flush()
        self._is_blanked = True

    def unblank(self):
        self.display.dpms_force_level(DPMSModeOn)
        self.display.flush()
        self._is_blanked = False

    def reset(self):
        img = self._get_background()
        photo = PhotoImage(img)
        self.panel.configure(image=photo)
        self.panel.image = photo
        self.panel.pack(side="bottom", fill="both", expand=1)

    def set_song(self, song: SongInfo, previous_song: SongInfo | None):
        song_details = SongDetails(song, previous_song)
        background = self._get_background()
        if song.album_cover:
            album_img = image_open(BytesIO(song.album_cover)).resize((360, 360))
            background.paste(album_img, (20, 60))
        else:
            placeholder_img = image_open(
                str(SHARE.joinpath("textured_grey.jpg"))
            ).resize((360, 360))
            background.paste(placeholder_img, (20, 60))

        background = song_details.draw(background)
        photo = PhotoImage(background)
        self.panel.configure(image=photo)
        self.panel.image = photo
        self.panel.pack(side="bottom", fill="both", expand=1)

    def start(self):
        def _tick():
            self.root.after(100, _tick)

        self.root.after(100, _tick)
        self.root.mainloop()

    def _get_background(self) -> Image:
        return image_open(str(SHARE.joinpath("grey_shadow_box.jpg")))
