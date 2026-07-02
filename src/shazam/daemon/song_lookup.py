import json
import re
from _sha2 import sha256
from asyncio import Task, TaskGroup
from datetime import datetime
from logging import getLogger
from typing import Any, Iterator

from httpx import AsyncClient, HTTPError
from pydantic import BaseModel, computed_field

from shazam.lib.db import DataMapper

logger = getLogger(__name__)


class SongInfo(BaseModel):
    title: str
    artist: str
    album: str
    source: str
    album_cover: bytes | None = None

    @computed_field
    @property
    def checksum(self) -> str:
        return sha256(
            (self.title or "").encode("utf-8") + (self.artist or "").encode("utf-8")
        ).hexdigest()


class SongLookup:
    MB_RELEASE_GROUP_URL: str = "https://musicbrainz.org/ws/2/release-group"
    MB_USER_AGENT: str = "shazam-daemon/1.0 (fitterj@gmail.com)"
    CAA_FRONT_URL: str = "https://coverartarchive.org/release/{mbid}/front"

    def __init__(
        self,
        db: DataMapper,
        client: AsyncClient,
        timeout: float = 8,
    ) -> None:
        self.db = db
        self.client: AsyncClient = client
        self.timeout: float = timeout

    async def get_song_info(self, response: dict[str, Any]) -> SongInfo:
        matches = self._extract_matches(response)
        spotify_meta = self._extract_spotify_metadata(matches)
        source = "spotify" if spotify_meta else "acrcloud"

        if spotify_meta:
            title = spotify_meta["title"]
            artist = spotify_meta["artist"]
            album_name = spotify_meta["album"]

        else:
            title, artist = self._track_and_artist(matches)
            fallback = self._oldest_fallback(matches)
            album_name = fallback["album"] if fallback else ""

        logger.info(f"Title: {title} Artist: {artist} Album: {album_name}")
        album = self.db.get_album(artist, album_name)
        cover = None
        if album and album.album_cover:
            logger.info("Using stored album")
            cover = album.album_cover

        return SongInfo(
            title=title,
            artist=artist,
            album=album_name,
            album_cover=cover,
            source=source,
        )

    async def get_album_cover(self, song: SongInfo) -> SongInfo:
        if len(song.artist) > 0 and len(song.album) > 0:
            song.album_cover = await self._fetch_mb_cover(
                self.client, song.artist, song.album
            )

        return song

    @staticmethod
    def _date_sort_key(value: str | None) -> str:
        if not value:
            return "9999-99-99"
        parts = value.split("-")
        if len(parts) == 1:
            return f"{value}-12-31"
        if len(parts) == 2:
            return f"{value}-31"
        return value

    @staticmethod
    def _extract_matches(response: dict) -> list[dict]:
        matches = (response.get("metadata", {}) or {}).get("music", []) or []
        return sorted(
            matches, key=lambda m: SongLookup._date_sort_key(m.get("release_date"))
        )

    @staticmethod
    def _extract_spotify_metadata(matches: list[dict]) -> dict | None:
        for m in sorted(matches, key=lambda m: m.get("score", 0), reverse=True):
            sp = (m.get("external_metadata", {}) or {}).get("spotify", {}) or {}
            track = sp.get("track") or {}
            album = sp.get("album") or {}
            artists = sp.get("artists") or []
            title = track.get("name")
            artist = artists[0].get("name") if artists else None
            if title and artist:
                return {"title": title, "artist": artist, "album": album.get("name")}
        return None

    @staticmethod
    def _track_and_artist(matches: list[dict]) -> tuple[str, str]:
        top = matches[0]
        title = top["title"]
        artists = top["artists"] or []
        artist = artists[0]["name"]
        return title, artist

    @staticmethod
    async def _fetch_image(client: AsyncClient, url: str) -> bytes | None:
        try:
            r = await client.get(url, follow_redirects=True)
            r.raise_for_status()
            return r.content
        except HTTPError:
            return None

    async def _fetch_mb_cover(
        self,
        client: AsyncClient,
        artist: str,
        album: str,
    ) -> bytes | None:
        logger.info(f"Fetching album art for {artist} {album}")
        candidates = [album]
        if "(" in album and ")" in album:
            candidates.append(re.sub(r"\s*\(.*?\)\s*", " ", album).strip())

        tasks: list[Task[list[dict[str, Any]]]] = []
        async with TaskGroup() as task_group:
            for candidate in candidates:
                tasks.append(
                    task_group.create_task(
                        self._fetch_mb_release_group(artist, candidate)
                    )
                )
        release_groups = [rg for t in tasks for rg in t.result()]
        logger.debug(json.dumps(release_groups))
        for mbid in self._iterate_releases(release_groups, album):
            cover = await self._fetch_image(
                client, self.CAA_FRONT_URL.format(mbid=mbid)
            )
            if cover:
                logger.info("Cover downloaded")
                return cover
        return None

    async def _fetch_mb_release_group(self, artist: str, album: str):
        try:
            response = await self.client.get(
                self.MB_RELEASE_GROUP_URL,
                params={
                    "query": f'artist:"{artist}" AND releasegroup:"{album}" AND primarytype:Album AND -secondarytype:Compilation',
                    "fmt": "json",
                },
                headers={"User-Agent": self.MB_USER_AGENT},
            )
            response.raise_for_status()
            return response.json().get("release-groups") or []
        except (HTTPError, ValueError):
            return []

    @staticmethod
    def _iterate_releases(release_groups: list[dict], album: str) -> Iterator[str]:
        album_l = album.lower()
        matching = [
            rg for rg in release_groups if album_l in rg.get("title", "").lower()
        ] or release_groups

        matching.sort(
            key=lambda rg: SongLookup._date_sort_key(rg.get("first-release-date"))
        )

        for rg in matching:
            releases = rg.get("releases") or []
            if releases:
                logger.info(f"Using MusicBrainz release group: {rg['title']}")
                for release in releases:
                    yield release["id"]

    @staticmethod
    def _parse_release_date(value: str | None) -> datetime:
        if not value:
            return datetime.max
        for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return datetime.max

    def _oldest_fallback(self, matches: list[dict]) -> dict[str, str] | None:
        dated: list[tuple[datetime, str]] = []
        for m in matches:
            album = (m.get("album") or {}).get("name")
            if not album:
                continue
            dated.append((self._parse_release_date(m.get("release_date")), album))

        if not dated:
            return None

        dated.sort(key=lambda d: d[0])
        return {"album": dated[0][1]}
