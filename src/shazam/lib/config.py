from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    db_url: AnyUrl
    acr_host: str
    acr_access_key: str
    acr_access_secret: str
    title_font_size: int
    other_font_size: int
    header_font_size: int
    previous_song_font_size: int


__config = Config()


def get_config() -> Config:
    return __config
