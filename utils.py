"""Commonly used utility functions."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import shutil
from time import sleep
from typing import Any, Callable
from openai import RateLimitError
import streamlit as st
from dotenv import load_dotenv

from natsort import natsorted


MAX_WORKERS = 15
MAX_429_RETRIES = 5
BASE_BACKOFF_SECONDS = 2


def delete_directory_contents(directory: str):
    if directory.startswith("/") or ".." in directory:
        raise ValueError(
            f"Refusing to delete {directory}, you can only delete directories from the "
            "base project root."
        )
    shutil.rmtree(directory, ignore_errors=True)
    os.makedirs(directory, exist_ok=True)


def get_env_var(var_name: str) -> str:
    """
    Read an environment variable and raise an error if it's missing
    """
    try:
        if var_name not in os.environ:
            raise EnvironmentError(f"Missing required environment variable: {var_name}")
        return os.environ[var_name]
    except OSError:
        load_dotenv()
        if var_name not in os.environ:
            raise EnvironmentError(f"Missing required environment variable: {var_name}")
        return os.environ[var_name]


def get_api_key() -> str:
    """
    Returns the API key
    """
    return get_env_var("OPENAI_API_KEY")


def get_all_image_paths(directory: str):
    paths = []
    for file in os.listdir(directory):
        if file.lower().endswith((".png", ".jpg", ".jpeg")):
            paths.append(os.path.join(directory, file))
    return natsorted(paths)


def log_message(message, display_mode):
    """Logs messages to console or Streamlit depending on display mode."""
    if display_mode:
        st.write(message)
    print(message)


def run_parallel_batches_with_retry(
    batch_jobs: list[dict[str, Any]],
    call_fn: Callable[[dict[str, Any]], Any],
    progress_callback=None,
) -> dict[str, Any]:
    """
    Runs batches in parallel and retries only 429-failed batch IDs.
    """
    pending_jobs: dict[str, dict[str, Any]] = {
        job["batch_id"]: job for job in batch_jobs
    }
    successful_results: dict[str, Any] = {}

    for attempt in range(MAX_429_RETRIES + 1):
        if not pending_jobs:
            return successful_results

        failed_batch_ids: list[str] = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_batch_id = {
                executor.submit(call_fn, job): batch_id
                for batch_id, job in pending_jobs.items()
            }

            for future in as_completed(future_to_batch_id):
                batch_id = future_to_batch_id[future]
                try:
                    successful_results[batch_id] = future.result()
                    if progress_callback:
                        progress_callback()
                except RateLimitError:
                    failed_batch_ids.append(batch_id)

        pending_jobs = {
            batch_id: pending_jobs[batch_id] for batch_id in failed_batch_ids
        }

        if pending_jobs and attempt < MAX_429_RETRIES:
            sleep(BASE_BACKOFF_SECONDS * (2**attempt))

    if pending_jobs:
        raise RuntimeError(
            "Rate-limited batches exhausted retries: "
            + ", ".join(sorted(pending_jobs.keys()))
        )

    return successful_results
