import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    ForeignKey,
    LargeBinary,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    Session,
    mapped_column,
    relationship,
)

from shazam.lib.config import get_config

config = get_config()
engine = create_engine(str(config.db_url))


class Base(MappedAsDataclass, DeclarativeBase):
    type_annotation_map = {
        uuid.UUID: UUID(as_uuid=True),
        str: Text,
        bytes: LargeBinary,
        datetime: TIMESTAMP(timezone=True),
    }


def get_session() -> Session:
    return Session(engine)


class Album(Base):
    __tablename__ = "album"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default_factory=uuid.uuid4,
        init=False,
    )
    artist: Mapped[str] = mapped_column()
    name: Mapped[str] = mapped_column()
    album_cover: Mapped[bytes | None] = mapped_column(default=None)


class Song(Base):
    __tablename__ = "song"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default_factory=uuid.uuid4,
        init=False,
    )

    title: Mapped[str] = mapped_column()
    artist: Mapped[str] = mapped_column()
    album_name: Mapped[str] = mapped_column()
    album_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("album.id"), default=None
    )
    played_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        init=False,
    )

    album: Mapped[Album | None] = relationship(default=None, init=False)


class DataMapper:
    def __init__(self, session: Session):
        self.session = session

    def get_album(self, artist: str, album_name: str) -> Album | None:
        return self.session.execute(
            select(Album).filter_by(artist=artist, name=album_name)
        ).scalar_one_or_none()

    def log_song(
        self, title: str, artist: str, album_name: str, album_cover: bytes | None
    ):
        album = self.session.execute(
            select(Album).filter_by(artist=artist, name=album_name)
        ).scalar_one_or_none()
        if not album:
            album = Album(artist=artist, name=album_name, album_cover=album_cover)
            self.session.add(album)
            self.session.flush()

        if album_cover and album and not album.album_cover:
            album.album_cover = album_cover
            self.session.add(album)

        self.session.add(
            Song(title=title, artist=artist, album_name=album_name, album_id=album.id)
        )
        self.session.commit()
