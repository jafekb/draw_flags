import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Optional

import aiohttp
from async_set import AsyncSet
from http_status import HTTPStatus
from rich.progress import (
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TimeElapsedColumn,
)
from unidecode import unidecode
from utils import category2dirname

NUM_MAPPERS = 1
NUM_FETCHERS = 3
NUM_DOWNLOADERS = 10

# Setup logger
logging.basicConfig(
    filename="log.log",
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# MediaWiki Endpoints
LIST_SUBCATEGORIES_ENDPOINT = "https://commons.wikimedia.org/w/api.php?action=query&list=categorymembers&cmtitle={title}&cmtype=subcat&format=json&utf8"
LIST_IMAGES_ENDPOINT = "https://commons.wikimedia.org/w/api.php?action=query&generator=categorymembers&gcmtitle={title}&gcmlimit=max&gcmtype=file&prop=imageinfo&iiprop=url&format=json&utf8"

# The maximum number of pages
MAX_PAGES = 50


async def request(url: str, *, session: aiohttp.ClientSession):
    """Asynchronously makes a GET request to the specified URL."""
    async with session.get(url) as response:
        status = response.status

        if status == HTTPStatus.OK:
            data = await response.read()
            contents = json.loads(data)
        else:
            contents = None

        return contents, status


async def request_and_retry(
    url: str,
    *,
    session: aiohttp.ClientSession,
    retries: int = -1,
) -> Optional[dict]:
    """Asynchronously makes a GET request to the specified URL and retries if the request fails."""
    failures = 0

    while retries == -1 or failures < retries:
        contents, status = await request(url, session=session)

        if status == HTTPStatus.OK:
            return contents
        if status == HTTPStatus.TOO_MANY_REQUESTS:
            logging.warning(f"Too many requests when accessing {url}. Retrying in 5 seconds...")
            await asyncio.sleep(5)
            failures += 1
        else:
            logging.error(f"Failed to make the request to {url}. Status code: {status}.")

    logging.error(f"Failed to make the request to {url} after {retries} retries.")
    return None


async def get_subcategories_no_continue(
    url: str,
    title: str,
    *,
    session: aiohttp.ClientSession,
) -> AsyncGenerator:
    """Asynchronously fetches the subcategories of the specified category,
    given the request URL. Does not handle continuation."""
    contents = await request_and_retry(url, session=session)

    # TODO(bjafek): KeyError: 'query'
    if "query" not in contents:
        logging.error(
            f"Got malformed response when listing subcategories of "
            f"'{title}'.\n{json.dumps(contents, indent=4)}"
        )
        return

    should_continue = "continue" in contents
    cmcontinue = contents["continue"]["cmcontinue"] if should_continue else None

    for subcategory in contents["query"]["categorymembers"]:
        yield subcategory["title"], should_continue, cmcontinue


async def get_subcategories(
    title: str,
    *,
    session: aiohttp.ClientSession,
) -> AsyncGenerator:
    """Asynchronously lists all immediate subcategories of the specified category."""
    endpoint = LIST_SUBCATEGORIES_ENDPOINT.format(title=title)

    should_continue = False
    cmcontinue = None

    async for subcategory, should_continue, cmcontinue in get_subcategories_no_continue(
        endpoint,
        title,
        session=session,
    ):
        yield subcategory

    while should_continue:
        continuation_endpoint = endpoint + "&cmcontinue=" + cmcontinue

        async for (
            subcategory,
            should_continue,
            cmcontinue,
        ) in get_subcategories_no_continue(
            continuation_endpoint,
            title,
            session=session,
        ):
            yield subcategory


async def map_categories(
    title: str,
    category_queue: asyncio.Queue,
    unmapped_category_queue: asyncio.Queue,
    seen_categories: AsyncSet,
    *,
    output_path: Path,
    mapper_id: int,
    progress: Progress,
    task: TaskID,
):
    """Asynchronously maps all recursive subcategories of the specified category,
    filling them into the provided queue."""
    total = 1

    async with aiohttp.ClientSession() as session:
        while not unmapped_category_queue.empty():
            try:
                title, dirpath = unmapped_category_queue.get_nowait()
                progress.update(task, advance=1, total=total)

                async for subcategory in get_subcategories(title, session=session):
                    is_new_category = await seen_categories.add_if_missing(subcategory)

                    if is_new_category:
                        subdirpath = dirpath / category2dirname(subcategory)

                        await category_queue.put((subcategory, subdirpath))
                        await unmapped_category_queue.put((subcategory, subdirpath))

                        total += 1
                        progress.update(task, advance=0, total=total)
                    else:
                        logging.debug(f"Loop detected at {subcategory}.")

                unmapped_category_queue.task_done()
            except KeyboardInterrupt:  # noqa: PERF203
                return
            except Exception as e:
                logging.error(
                    "A task exited after it encountered an unexpected error while "
                    f"mapping categories: {e}"
                )

    if mapper_id == 0:
        num_categories = await seen_categories.size()
        logging.debug(f"Discovered {num_categories} categories.")

        progress.update(task, visible=False, refresh=True)


async def spawn_category_mappers(
    title: str,
    category_queue: asyncio.Queue,
    seen_categories: AsyncSet,
    *,
    output_path: Path,
    num_mappers: int,
    progress: Progress,
    task: TaskID,
):
    """Spawns the asynchronous category mapper tasks."""
    dirpath = output_path / category2dirname(title)

    unmapped_category_queue = asyncio.Queue()

    await category_queue.put((title, dirpath))
    await unmapped_category_queue.put((title, dirpath))

    tasks = []

    for mapper_id in range(num_mappers):
        task = asyncio.create_task(
            map_categories(
                title,
                category_queue,
                unmapped_category_queue,
                seen_categories,
                output_path=output_path,
                mapper_id=mapper_id,
                progress=progress,
                task=task,
            ),
        )
        tasks.append(task)

    return tasks


async def get_images_no_continue(
    url: str,
    *,
    session: aiohttp.ClientSession,
) -> AsyncGenerator:
    """Asynchronously fetches the images of the specified category, given
    the request URL. Does not handle continuation."""
    contents = await request_and_retry(url, session=session)

    # There are no images on this page
    if "query" not in contents:
        return

    should_continue = "continue" in contents

    if "continue" in contents:
        should_continue = True

        if "gcmcontinue" in contents["continue"]:
            continuation_param = "gcmcontinue"
            continuation_value = contents["continue"]["gcmcontinue"]
        elif "iistart" in contents["continue"]:
            continuation_param = "iistart"
            continuation_value = contents["continue"]["iistart"]
    else:
        should_continue = False
        continuation_param = None
        continuation_value = None

    for page in contents["query"]["pages"].values():
        title = page["title"]

        # TODO(bjafek): Check this
        if len(page["imageinfo"]) > 1:
            logging.warning(f'Found more than one image for page "{title}".')

        url = page["imageinfo"][0]["url"]
        yield title, url, should_continue, continuation_param, continuation_value


async def get_images(
    title: str,
    *,
    session: aiohttp.ClientSession,
) -> AsyncGenerator:
    """Asynchronously lists all images under the specified categories."""
    endpoint = LIST_IMAGES_ENDPOINT.format(title=title)

    should_continue = False
    continuation_param = None
    continuation_value = None

    async for (
        image_title,
        image_url,
        should_continue,
        continuation_param,
        continuation_value,
    ) in get_images_no_continue(endpoint, session=session):
        yield image_title, image_url

    while should_continue:
        continuation_endpoint = endpoint + f"&{continuation_param}={continuation_value}"

        async for (
            image_title,
            image_url,
            should_continue,
            continuation_param,
            continuation_value,
        ) in get_images_no_continue(continuation_endpoint, session=session):
            yield image_title, image_url


async def fetch_images(
    category_queue: asyncio.Queue,
    download_queue: asyncio.Queue,
    seen_images: AsyncSet,
    *,
    progress: Progress,
    task: TaskID,
):
    """Asynchronously fetches images from the specified category and
    submit them to the downloaders."""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                title, dirpath = await category_queue.get()

                # Received stop signal from the mapper tasks
                if title is None:
                    break

                async for image_title, image_url in get_images(title, session=session):
                    is_new_image = await seen_images.add_if_missing(image_url)
                    # TODO(bjafek) is there ever a time when the unicode conversion won't
                    #  be able to find the wikipedia page? I tried a few examples and it
                    #  worked fine.
                    image_name = unidecode(image_title.replace("File:", ""))
                    image_path = dirpath / image_name
                    just_page = re.search(r"Flag of ([a-z\ A-Z,\.\-]*)", image_name)
                    if just_page is not None:
                        just_page = just_page.group(1).split(".")[0]

                    # TODO(bjafek) this is a little bit clumsy
                    if is_new_image and just_page:
                        await download_queue.put((image_url, image_path, just_page))
                        total = await seen_images.size()
                        progress.update(task, total=total)
                    else:
                        logging.debug('Skipping duplicate image "{image_title}".')

                category_queue.task_done()
            except KeyboardInterrupt:
                return
            except Exception as e:
                logging.error(
                    "A task exited after it encountered an unexpected error "
                    f"while downloading images: {e}"
                )


async def spawn_image_fetchers(
    category_queue: asyncio.Queue,
    download_queue: asyncio.Queue,
    seen_images: AsyncSet,
    *,
    num_fetchers: int,
    progress: Progress,
    task: TaskID,
):
    """Spawns the asynchronous image fetcher tasks."""
    image_fetchers = []

    for _ in range(num_fetchers):
        image_fetcher = asyncio.create_task(
            fetch_images(
                category_queue,
                download_queue,
                seen_images,
                progress=progress,
                task=task,
            ),
        )
        image_fetchers.append(image_fetcher)

    return image_fetchers


async def download_image(
    image_url: str,
    image_path: str,
    just_page: str,
    *,
    session: aiohttp.ClientSession,
):
    """Asynchronously downloads the image from the specified URL to the specified path."""
    image_path.parent.mkdir(exist_ok=True, parents=True)

    async with session.get(image_url) as response:
        if response.status == HTTPStatus.OK:
            with image_path.open("wb") as file:
                file.write(await response.read())

            # TODO(bjafek) do this better.
            data_path = image_path.replace("/Flags/", "/data/")
            data_path.parent.mkdir(exist_ok=True)
            out_name = data_path.parent / f"{image_path.stem}.json"
            data = {
                "just_page": just_page,
                "image_url": image_url,
                "image_path": image_path,
                "out_name": out_name,
            }
            with out_name.open("w") as f:
                json.dump(data, f, indent=1)

        else:
            logging.error(
                f"Failed to download image from {image_url}. Status code: {response.status}."
            )


async def download_images(
    download_queue: asyncio.Queue,
    seen_images: AsyncSet,
    *,
    progress: Progress,
    task: TaskID,
):
    async with aiohttp.ClientSession() as session:
        while True:
            image_url, image_path, just_page = await download_queue.get()

            # Received the stop signal from the fetcher tasks
            if image_url is None:
                break

            if not image_path.is_file():
                await download_image(image_url, image_path, just_page, session=session)

            total = await seen_images.size()
            progress.update(task, advance=1, total=total)


async def spawn_image_downloaders(
    download_queue: asyncio.Queue,
    seen_images: AsyncSet,
    *,
    num_downloaders: int,
    progress: Progress,
    task: TaskID,
):
    """Spawns the asynchronous image downloader tasks."""
    image_downloaders = []

    for _ in range(num_downloaders):
        image_downloader = asyncio.create_task(
            download_images(download_queue, seen_images, progress=progress, task=task),
        )
        image_downloaders.append(image_downloader)

    return image_downloaders


async def main():
    # TODO(bjafek) command-line flag
    categories_filepath = Path(
        "/home/bjafek/personal/draw_flags/data_mining/wikimedia-downloader/text_file.txt"
    )

    titles = []

    with categories_filepath.open() as file:
        for line in file:
            title = "Category:" + line.strip()
            titles.append(title)

    # TODO(bjafek) command-line flag
    output_path = Path("/home/bjafek/personal/draw_flags/data_mining/wikimedia-downloader/dogs")

    progress = Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        transient=True,
        refresh_per_second=10,
    )

    category_queue = asyncio.Queue()
    download_queue = asyncio.Queue()

    seen_categories = AsyncSet(titles)
    seen_images = AsyncSet()

    with progress:
        mapper_tasks = []

        for title in titles:
            task = progress.add_task(f'[blue]Mapping "{title}"...', total=None)
            category_mappers = await spawn_category_mappers(
                title,
                category_queue,
                seen_categories,
                output_path=output_path,
                num_mappers=NUM_MAPPERS,
                progress=progress,
                task=task,
            )
            mapper_tasks.extend(category_mappers)

        # Spawn image fetchers and downloaders
        task = progress.add_task("[green]Downloading images...", total=None)

        fetcher_tasks = await spawn_image_fetchers(
            category_queue,
            download_queue,
            seen_images,
            num_fetchers=NUM_FETCHERS,
            progress=progress,
            task=task,
        )

        downloader_tasks = await spawn_image_downloaders(
            download_queue,
            seen_images,
            num_downloaders=NUM_DOWNLOADERS,
            progress=progress,
            task=task,
        )

        await asyncio.gather(*mapper_tasks)

        num_categories = await seen_categories.size()
        logging.info(f"Found {num_categories} categories.")

        # Submit stop signals to the fetchers
        for _ in range(NUM_FETCHERS):
            await category_queue.put((None, None))

        await asyncio.gather(*fetcher_tasks)

        logging.info("Submitted all images to the download queue.")

        # Submit stop signals to the downloaders
        for _ in range(NUM_DOWNLOADERS):
            await download_queue.put((None, None, None))

        await asyncio.gather(*downloader_tasks)

        num_images = await seen_images.size()
        logging.info(f"Finished downloading {num_images} images.")


if __name__ == "__main__":
    asyncio.run(main())
