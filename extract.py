"""
EXTRACT: download the raw files.

- Tries the download several times (retries) with a growing wait between tries.
- Saves each file to data/raw/ so the original is never changed.
- If the download fails but an earlier copy exists, uses that copy and logs a warning.
"""
import logging
import os
import time

import requests

import config

log = logging.getLogger("pipeline.extract")


def download_file(file_name: str) -> str:
    """Download one file and return the local path where it was saved."""
    os.makedirs(config.RAW_DIR, exist_ok=True)
    url = config.BASE_URL + file_name
    local_path = os.path.join(config.RAW_DIR, file_name)

    for attempt in range(1, config.DOWNLOAD_RETRIES + 1):
        try:
            log.info("Downloading %s (try %d of %d)", file_name, attempt, config.DOWNLOAD_RETRIES)
            response = requests.get(url, timeout=config.DOWNLOAD_TIMEOUT)
            response.raise_for_status()          # stop if the server says 404, 500, ...
            with open(local_path, "wb") as f:
                f.write(response.content)
            log.info("Saved %s (%d bytes)", local_path, len(response.content))
            return local_path
        except requests.RequestException as error:
            log.warning("Download failed: %s", error)
            if attempt < config.DOWNLOAD_RETRIES:
                wait = 2 ** attempt               # wait 2s, then 4s, then 8s ...
                log.info("Waiting %d seconds before trying again", wait)
                time.sleep(wait)

    # Every try failed. Fall back to an earlier copy if we have one.
    if os.path.exists(local_path):
        log.warning("Using previously downloaded copy of %s", file_name)
        return local_path
    raise RuntimeError(f"Could not download {file_name} and no local copy exists")


def extract_all() -> dict:
    """Download every source file. Returns {source_name: local_path}."""
    return {name: download_file(file_name) for name, file_name in config.SOURCES.items()}
