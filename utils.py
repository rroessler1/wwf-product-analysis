"""Commonly used utility functions."""

import os
import streamlit as st

from natsort import natsorted

from settings import API_KEY_ENV_VAR_NAME


def get_env_var(var_name: str) -> str:
    """
    Read an environment variable and raise an error if it's missing
    """
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
