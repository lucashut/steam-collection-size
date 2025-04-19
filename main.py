"""
A script that downloads a Steam Workshop collection page and
sorts the items by size. It is multi-threaded to speed up the
process. The results can be saved to a log file.
"""

import os
import logging
from threading import Thread, Event
from concurrent.futures import ThreadPoolExecutor
from argparse import ArgumentParser
from typing import List, Tuple
from requests import Session, Timeout, HTTPError, RequestException
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup as BS, Tag


# Aliases
ItemsInfoList = List[Tuple[str, str, float]]

# Constants
LOG_FILE = "logs/log.txt"
URL_FORMAT = "https://steamcommunity.com/sharedfiles/filedetails/?id="
EXIT_EVENT = Event()
TIMEOUT_SECONDS = 0.8
RETRY_COUNT = 3
KILOBYTE = 1024
MEGABYTE = KILOBYTE * KILOBYTE
GIGABYTE = MEGABYTE * KILOBYTE

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def get_size_unit(size: float, trunc: bool = False) -> str:
    """Converts a size in bytes to a human-readable format."""
    units = ['bytes', 'KB', 'MB', 'GB']
    unit_index = 0

    while size >= KILOBYTE and unit_index < len(units) - 1:
        size /= KILOBYTE
        unit_index += 1

    size_str = f"{size:.2f}" if trunc else f"{size:.0f}"
    return f"{size_str} {units[unit_index]}"


def size_to_bytes(size: str) -> float:
    """Converts a size string to bytes."""
    multipliers = {'KB': 1024, 'MB': 1024 * 1024, 'GB': 1024 * 1024 * 1024}
    num, unit = size.split()
    return float(num) * multipliers.get(unit, 1)


def download_page(url: str) -> BS:
    """
    Downloads the content of a web page and
    returns it as a BeautifulSoup object.
    """
    try:
        with Session() as session:
            retry = Retry(total=RETRY_COUNT, backoff_factor=1,
                          status_forcelist=[502, 503, 504])
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('https://', adapter)

            response = session.get(url, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            return BS(response.content, 'html.parser')

    except Timeout:
        logging.error("Timeout occurred while accessing %s", url)
    except HTTPError as e:
        logging.error("HTTP error occurred: %s", e)
    except RequestException as e:
        logging.error("Request exception: %s", e)

    return BS("<error>Failed to download page</error>", 'html.parser')


def get_addon_size(page: BS) -> str:
    """Returns the size of an addon."""
    size_tag = page.find('div', class_="detailsStatRight")
    return size_tag.text if size_tag else "0 KB"


def get_item_name(item: Tag) -> str:
    """Returns the name of an item."""
    return item.find('div', class_="workshopItemTitle").text


def get_item_url(item: Tag) -> str:
    """Returns the URL of an item."""
    return item.find('a').get('href')


def get_collection_items(page: BS) -> List[Tag]:
    """Returns a list of collection items from a BS page."""
    return page.find_all('div', class_="collectionItem")


def get_item_size_bytes(item_url: str, item_name: str) -> float:
    """Download item page and get its size."""
    item_page: BS = download_page(item_url)
    size_in_bytes: float = 0

    if not item_page.find('error'):
        size_in_bytes = size_to_bytes(get_addon_size(item_page))
        logging.info("%s", f"Done downloading: {item_name}")

    return size_in_bytes


def worker(results: ItemsInfoList, index: int) -> None:
    """Worker function for size downloading threads."""
    url, name, _ = results[index]
    size = get_item_size_bytes(url, name)
    results[index] = [url, name, size]


def get_items_info(collection_page: BS) -> ItemsInfoList:
    """Returns a dictionary of collection item sizes."""
    items: List[Tag] = get_collection_items(collection_page)
    info: ItemsInfoList = [["", "", 0.0]] * len(items)

    logging.info("%s", f"{len(items)} item(s) found.")
    logging.info("%s", "Collecting information now...\n")

    def process_item(index: int):
        item = items[index]
        item_url: str = get_item_url(item)
        item_name: str = get_item_name(item)
        size = get_item_size_bytes(item_url, item_name)
        info[index] = [item_url, item_name, size]

    with ThreadPoolExecutor() as executor:
        executor.map(process_item, range(len(items)))

    return info


def sort_collection_by_size(items_array: ItemsInfoList )-> ItemsInfoList:
    """Sorts the bi-dimentional array by size of item."""
    return sorted(
        ((url, name, size) for url, name, size in items_array),
        key=lambda x: x[2],
        reverse=True
    )


def get_collection_sorted(url: str) -> ItemsInfoList:
    """Prints the collection items sorted by size."""
    if not url.startswith(URL_FORMAT):
        raise ValueError(f"URL must follow the format: '{URL_FORMAT}'")

    collection_page: BS = download_page(url)
    if collection_page.find('error'):
        error: str = collection_page.find('error').text
        logging.error("%s", f"Error downloading collection {url}: {error}")
        raise ValueError(error)

    collection_items: ItemsInfoList = get_items_info(collection_page)

    return sort_collection_by_size(collection_items)


def format_log(item_list: ItemsInfoList) -> str:
    """Creates a table like string with the items list."""
    max_size_len: int = max(
        len(get_size_unit(size)) for _, _, size in item_list)
    max_name_len: int = max(len(name) for _, name, _ in item_list)
    str_list: str = ""

    for i, (url, name, size) in enumerate(item_list):
        str_list += f"{ str(i).zfill(3) } | "
        str_list += f"{ get_size_unit(size):>{max_size_len}} | "
        str_list += f"{ name:>{max_name_len}} | {url}"
        str_list += "\n"

    return str_list


def save_log(url: str, item_list: str, size: str, save_path: str = None):
    """Saves the log to a file."""
    if not save_path:
        save_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), LOG_FILE)

    with open(save_path, "w", encoding='utf-8') as file:
        file.write(
            f"Steam Workshop collection sorted by size: {url}\n\n" +
            f"Total size: {size}\n\n" +
            f"{item_list}\n")

        logging.info("%s", f"Log saved to {LOG_FILE}.")


if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument(
        "url", type=str, help="URL of the collection.")
    parser.add_argument(
        "-s", "--log", action="store_true", help="Don't ask to save the log.")
    parser.add_argument(
        "-o", "--output", type=str, help="Path to save the log file.")

    args = parser.parse_args()

    try:
        steam_url: str = args.url
        sorted_collection: ItemsInfoList = get_collection_sorted(steam_url)
        total_size_bytes: float = sum(size for _, _, size in sorted_collection)
        total_size_formatted: str = get_size_unit(total_size_bytes, trunc=True)
        text_list: str = format_log(sorted_collection)

        logging.info("%s", f"Collection sorted by items size:\n{text_list}\n")
        logging.info("%s", f"Total size: {total_size_formatted}\n")

        write_log: bool = args.log

        if not write_log:
            logging.info("%s", "Save the log to a file? (y/n): ")
            write_log = input().lower() == 'y'

        if write_log:
            save_log(steam_url, text_list, total_size_formatted, args.output)


    except KeyboardInterrupt:
        logging.info("Interrupted by user. Exiting...")
