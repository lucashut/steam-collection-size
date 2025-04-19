"""
This script retrieves the items of a Steam collection and sorts them by size.
"""

import logging
from threading import Thread
from argparse import ArgumentParser
from typing import List, Tuple, Dict
import requests
from requests.adapters import HTTPAdapter, Retry
import os

# Aliases
ItemsInfoList = List[Tuple[str, str, float]]

# Constants
LOG_FILE = "logs/log.txt"
CONTENT_URL_FORMAT = "https://steamcommunity.com/sharedfiles/filedetails/?id="
TIMEOUT_SECONDS = 5
RETRY_COUNT = 5
KILOBYTE = 1024
MEGABYTE = KILOBYTE * KILOBYTE
GIGABYTE = MEGABYTE * KILOBYTE

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def download_collection_data(steam_id: str) -> str:
    url = "https://api.steampowered.com/ISteamRemoteStorage/GetCollectionDetails/v1/"

    data = {
        "collectioncount": 1,
        "publishedfileids[0]": steam_id
    }

    try:
        session = requests.Session()
        retry = Retry(total=RETRY_COUNT, backoff_factor=1, status_forcelist=[ 502, 503, 504 ])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        response = session.post(url, data=data, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.Timeout as exc:
        logging.error("Timeout error while getting collection %s.", steam_id)
        raise SystemExit(1) from exc

    return response.json()['response']


def download_item_data(item_id: str) -> Dict:
    url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"

    data = {
        "itemcount": 1,
        "publishedfileids[0]": item_id
    }

    try:
        session = requests.Session()
        retry = Retry(total=RETRY_COUNT, backoff_factor=1, status_forcelist=[ 502, 503, 504 ])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        response = session.post(url, data=data, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.Timeout as exc:
        logging.error("Timeout error while getting item %s.", item_id)
        raise ValueError(f"Timeout error while getting item {item_id}.") from exc
    
    #except requests.exceptions.Timeout as exc:
    #    logging.error("Timeout error while getting collection %s.", steam_id)
    #    raise SystemExit(1) from exc
    
    return response.json()['response']


def get_size_unit(size: float) -> str:
    """Converts a size in bytes to a human-readable format."""
    su: str = ""

    for unit in ['bytes', 'KB', 'MB', 'GB']:
        if size < KILOBYTE:
            su = f"{size:.2f} {unit}"
            break
        size /= KILOBYTE

    return su


def get_item_name_and_size(item_id: str) -> Tuple[str, float]:
    """Get the infomation of an item using the Steam API."""
    data = download_item_data(item_id)
    title: str = "unavailable"
    size: float = 0.0

    try:
        if data['publishedfiledetails'][0]['result'] == 1:  # OK status
            #print(f"{data}\n\n")
            title: str = data['publishedfiledetails'][0]['title']
            size: float = float(data['publishedfiledetails'][0]['file_size'])
    except:
        print(f"{data}\n\n")

    return [title, size]


def get_items_info(items_list: ItemsInfoList) -> ItemsInfoList:
    """Get the information of collection items using the Steam API."""
    threads: List[Thread] = []

    items_list = items_list[:]

    logging.info("%s", f"{len(items_list)} item(s) found.")
    logging.info("%s", "Collecting information now...\n")

    for i, _ in enumerate(items_list):
        th: Thread = Thread(target=worker, args=(items_list, i))
        threads.append(th)
        th.start()

    for thread in threads:
        thread.join()

    return items_list


def worker(results: ItemsInfoList, index: int) -> None:
    """Worker function for size downloading threads."""
    item_id, _, _ = results[index]
    results[index] = [item_id, *get_item_name_and_size(item_id)]
    logging.info("%s", f"Done downloading: {results[index][1]}")


def get_collection_items(steam_id: str) -> ItemsInfoList:
    """Get the items of a collection using the Steam API."""
    data = download_collection_data(steam_id)
    items_dict: List[Dict] = data['collectiondetails'][0]['children']
    items_list: ItemsInfoList = [[item['publishedfileid'], "", 0.0] for item in items_dict]

    return get_items_info(items_list)


def sort_collection_by_size(unsorted_items: ItemsInfoList) -> ItemsInfoList:
    """Return the collection sorted by size."""
    return sorted(
        ((item_id, title, size) for item_id, title, size in unsorted_items),
        key=lambda x: x[2],
        reverse=True
    )


def format_log(item_list: ItemsInfoList):
    """Creates a table like string with the items list."""
    max_size_len: int = max(len(get_size_unit(size)) for _, _, size in item_list)
    max_name_len: int = max(len(name) for _, name, _ in item_list)
    str_list: str = ""

    for i, (url, name, size) in enumerate(item_list):
        str_list += f"{ str(i).zfill(3) } | "
        str_list += f"{ get_size_unit(size):>{max_size_len}} | "
        str_list += f"{ name:<{max_name_len}} | {url}"
        str_list += "\n"

    return str_list


def save_log(url: str, item_list: str, size: str, save_path: str = None):
    """Saves the log to a file."""
    if not save_path:
        save_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), LOG_FILE)

    with open(save_path, "w", encoding='utf-8') as file:
        file.write(
            f"Steam Workshop collection sorted by size (ID): {url}\n\n" +
            f"Total size: {size}\n\n" +
            f"{item_list}\n")

        logging.info("%s", f"Log saved to {LOG_FILE}.")


if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument("collection_id", type=str, help="The ID of the collection.")
    args = parser.parse_args()

    try:
        collection_id: str = args.collection_id
        collection_items: ItemsInfoList = get_collection_items(collection_id)
        sorted_collection: ItemsInfoList = sort_collection_by_size(collection_items)

        total_size_bytes: float = sum(size for _, _, size in sorted_collection)
        size_and_unit: str = get_size_unit(total_size_bytes)
        text_list: str = format_log(sorted_collection)

        logging.info("%s", f"Collection sorted by items size:\n{text_list}\n")
        logging.info("%s", f"Total size: {size_and_unit}\n")

        save_log(collection_id, text_list, size_and_unit)

    except KeyboardInterrupt:
        logging.info("Interrupted by user. Exiting...")
