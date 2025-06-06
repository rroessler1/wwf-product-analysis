"""Commonly used utility functions."""

import os
import shutil
import streamlit as st
from dotenv import load_dotenv

from natsort import natsorted

from settings import API_KEY_ENV_VAR_NAME


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
    return get_env_var(API_KEY_ENV_VAR_NAME)


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
