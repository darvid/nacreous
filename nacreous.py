# -*- coding: utf-8 -*
"""nacreous

Downloads, tags, and embeds cover art in tracks from Soundcloud.

"""
import asyncio
import atexit
import codecs
import contextlib
import io
import os
import pathlib
import re
import sys
import time

import click
import furl
import logbook
import mutagen.easyid3
import mutagen.id3
import mutagen.mp3
import plumbum
import requests
import selenium.common.exceptions
import selenium.webdriver


__version__ = "0.0.1"


log = logbook.Logger(__name__)


BASE_URL = furl.furl("https://soundcloud.com/")

CSS_BGURL_PATTERN = re.compile(r"url\(['\"]?(.+?)['\"]?\)")
FULL_COVER_PATTERN = re.compile(
    br"(https://.+?\.sndcdn\.com/artworks-.+?500x500\.jpg)")

ARTWORK_SELECTOR = ".sc-artwork span"
LOADING_INDICATOR_SELECTOR = ".loading"
SOUND_SELECTOR = ".soundList__item"
SOUND_ANCHOR_SELECTOR = ".soundTitle__title"
TITLE_SELECTOR = SOUND_ANCHOR_SELECTOR
USERNAME_ANCHOR_SELECTOR = ".soundTitle__username"
USERNAME_SELECTOR = ".soundTitle__usernameText"

DEFAULT_YTDL_FILENAME_FMT = "%(uploader)s/%(title)s.%(ext)s"
DEFAULT_YTDL_OPTIONS = [
    "--audio-format", "mp3",
    "--output", DEFAULT_YTDL_FILENAME_FMT,
]

DEFAULT_COVER_MIME = "image/jpg"
DEFAULT_COVER_DESC = "Cover"

youtube_dl = plumbum.local["youtube-dl"][DEFAULT_YTDL_OPTIONS]


class Sound(object):

    def __init__(self, url, title, user, user_url, cover_thumbnail,
                 cover=None):
        self.url = url
        self.user = user
        self.user_url = user
        self.title = title
        self.cover_thumbnail = cover_thumbnail
        self.cover = cover or self.fetch_cover_url()

    @classmethod
    def from_element(cls, elem):
        try:
            cover_thumbnail = CSS_BGURL_PATTERN.match(
                elem.find_element_by_css_selector(ARTWORK_SELECTOR)
                .value_of_css_property("background-image")).group(1)
        except (AttributeError,
                selenium.common.exceptions.NoSuchElementException):
            cover_thumbnail = None
        return cls(
            url=elem.find_element_by_css_selector(
                SOUND_ANCHOR_SELECTOR).get_attribute("href"),
            title=elem.find_element_by_css_selector(TITLE_SELECTOR).text,
            user=elem.find_element_by_css_selector(USERNAME_SELECTOR).text,
            user_url=elem.find_element_by_css_selector(
                USERNAME_ANCHOR_SELECTOR).get_attribute("href"),
            cover_thumbnail=cover_thumbnail,
        )

    def fetch_cover(self):
        if self.cover_thumbnail is not None:
            log.debug("Fetching cover from {!r}", str(self.cover))
            return io.BytesIO(requests.get(str(self.cover)).content)

    def fetch_cover_url(self):
        if self.cover_thumbnail is not None:
            # XXX: don't really need to 'fetch' anything at all :-)
            self.cover = self.cover_thumbnail.replace("200x200", "500x500")
            return self.cover

    def __repr__(self):
        return "<Sound(user={!r}, title={!r})>".format(self.user, self.title)


def likes_url(user):
    return BASE_URL.copy().set(path=(user, "likes"))


def user_url(user):
    return BASE_URL.copy().set(path=(user, ))


# <https://code.activestate.com/recipes/576620-changedirectory-context-manager/#c3>
@contextlib.contextmanager
def working_directory(path):
    """A context manager which changes the working directory to the given
    path, and then changes it back to its previous value on exit.

    """
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


async def crawl_sounds(driver, url, queue, future, pages=-1):
    if driver.current_url != url:
        driver.get(url)
    current_page = 0
    current_selector = SOUND_SELECTOR
    num_sounds = 0
    while True:
        sound_elements = driver.find_elements_by_css_selector(current_selector)

        if current_selector != SOUND_SELECTOR and len(sound_elements) == 0:
            time.sleep(1)
            continue

        for elem in sound_elements:
            num_sounds += 1
            await queue.put(Sound.from_element(elem))

        current_selector = "{selector}:nth-child({after}) ~ {selector}".format(
            selector=SOUND_SELECTOR, after=num_sounds)

        scroll_to_bottom(driver)
        try:
            driver.find_element_by_css_selector(LOADING_INDICATOR_SELECTOR)
            time.sleep(0.01)
        except selenium.common.exceptions.NoSuchElementException:
            log.info("Reached end of page")
            break

        if pages != -1:
            if current_page >= pages:
                break
            else:
                current_page += 1

    log.debug("Crawl complete")
    await queue.join()
    future.set_result(num_sounds)


async def download_sounds(loop, queue, future, skip_existing=True):
    while True:
        if future.done():
            break
        sound = await queue.get()
        download_sound(sound, overwrite=not skip_existing)
        queue.task_done()


def tag_mp3(sound, filename, cover=None):
    mp3 = mutagen.mp3.MP3(filename, ID3=mutagen.id3.ID3)
    try:
        mp3.add_tags()
    except mutagen.id3.error:
        pass
    finally:
        mp3["TIT2"] = mutagen.id3.TIT2(
            encoding=mutagen.id3.Encoding.UTF8,
            text=sound.title)
        mp3["TPE1"] = mutagen.id3.TPE1(
            encoding=mutagen.id3.Encoding.UTF8,
            text=sound.user)
        if cover is not None:
            try:
                mp3.tags.add(
                    mutagen.id3.APIC(
                        encoding=mutagen.id3.Encoding.UTF8,
                        mime=DEFAULT_COVER_MIME,
                        type=mutagen.id3.PictureType.COVER_FRONT,
                        desc=DEFAULT_COVER_DESC,
                        data=cover.read(),
                    )
                )
            except mutagen.id3.error as err:
                log.warn(err)
    return mp3


def download_sound(sound, overwrite=False):
    filename = youtube_dl("--get-filename", sound.url).strip()
    if not overwrite and pathlib.Path(filename).exists():
        log.info("Skipping {!r}, already exists", sound.title)
        return False
    log.info("Downloading {!r}", sound.title)
    youtube_dl["-q", sound.url] & plumbum.FG
    log.debug("Saved {!r}", filename)
    cover = sound.fetch_cover()
    tag_mp3(sound, filename, cover).save()
    return True


def scroll_to_bottom(driver):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")


def start_webdriver(driver_name="Firefox", **kwargs):
    log.debug("Starting Selenium")
    driver = getattr(selenium.webdriver, driver_name)(**kwargs)
    atexit.register(driver.close)
    return driver


@click.group()
@click.option("--debug/--no-debug")
@click.pass_context
def main(ctx, debug):
    if sys.platform == "win32":
        codecs.register(lambda name: (codecs.lookup("utf-8")
                                      if name == "cp65001" else None))
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    logbook.StreamHandler(
        sys.stdout,
        level=logbook.DEBUG if debug else 0,
    ).push_application()


@main.command()
@click.option("-d", "--dest", default=str(pathlib.Path.home() / "Music"))
@click.option("-n", "--num-workers", type=int, default=10)
@click.option("-s", "--skip-existing", type=bool, default=True)
@click.option("--likes", "page", flag_value="likes")
@click.option("--user", "page", flag_value="user")
@click.argument("user")
@click.pass_obj
def sync(driver, dest, num_workers, skip_existing, page, user):
    """Downloads sounds."""
    loop = asyncio.get_event_loop()
    # loop.set_debug(True)
    sounds = asyncio.Queue(maxsize=num_workers)

    future = asyncio.Future()

    if page == "likes":
        url = str(likes_url(user))
    elif page == "user":
        url = str(user_url(user))

    try:
        tasks = [
            loop.create_task(crawl_sounds(
                url=url,
                driver=start_webdriver(),
                queue=sounds,
                future=future,
            )),
        ]
        tasks += [
            loop.create_task(download_sounds(
                loop=loop,
                queue=sounds,
                future=future,
                skip_existing=skip_existing,
            ))
            for _ in range(num_workers)
        ]
        with working_directory(dest):
            loop.run_until_complete(asyncio.wait(tasks))
    finally:
        loop.close()
