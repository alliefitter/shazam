from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    db_url: AnyUrl
    acr_host: str
    acr_access_key: str
    acr_access_secret: str


__config = Config()


def get_config() -> Config:
    return __config
