import streamlit as st
import json
import os

import settings
from settings import DEFAULT_SETTINGS

# --- Configuration Constants ---
SETTINGS_FILE = "user_settings.json"


def show_settings_page():
    """The dedicated settings page for user configuration."""
    st.title("Settings")

    # Get the current settings from the session state
    current_settings = st.session_state.settings

    # Use st.form for atomic saving
    with st.form("settings_form"):
        st.subheader("OpenAI Configuration")
        st.text(
            "Model names can be found here: https://platform.openai.com/docs/pricing"
        )
        st.text("\n")
        st.text_input(
            "OpenAI Image Model",
            value=current_settings[settings.IMAGE_MODEL_SETTING_KEY],
            key="temp_image_model",
            help="Enter the exact name of the OpenAI Image model to use (e.g. gpt-4.1-mini).",
        )

        st.text_input(
            "OpenAI Text Model",
            value=current_settings[settings.TEXT_MODEL_SETTING_KEY],
            key="temp_text_model",
            help="Enter the exact name of the OpenAI Text model to use (e.g. gpt-4.1-mini).",
        )

        api_key_placeholder = "Key is currently set. Leave blank to keep existing key."

        st.text_input(
            "New API Key",
            value="",  # IMPORTANT: Do not show the current key
            placeholder=api_key_placeholder,
            key="temp_api_key",
            type="password",
            help="Enter a new key to change it. If you leave this field empty, the currently saved key will be retained.",
        )

        # The form submission button calls the apply_settings function
        st.form_submit_button("Save", on_click=apply_settings)


def apply_settings():
    """
    Callback function to update permanent settings from the settings form inputs.
    Handles the sensitive API key logic.
    """
    # If the user left the API key blank, use the existing saved key.
    if st.session_state.temp_api_key == "":
        final_api_key = st.session_state.settings[settings.API_KEY_SETTING_KEY]
    # If the user entered something, use the new key.
    else:
        final_api_key = st.session_state.temp_api_key

    # 3. Create the final settings dictionary
    updated_settings = {
        settings.IMAGE_MODEL_SETTING_KEY: st.session_state.temp_image_model,
        settings.TEXT_MODEL_SETTING_KEY: st.session_state.temp_text_model,
        settings.API_KEY_SETTING_KEY: final_api_key,
    }

    # 4. Save the new configuration and update session state
    if save_settings(updated_settings):
        st.session_state.settings = updated_settings
        st.toast("Settings saved successfully!")


def load_settings():
    """Reads settings from the JSON file or returns defaults if the file is not found."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
                # Ensure all default keys are present even if file is older
                return {**DEFAULT_SETTINGS, **settings}
        except json.JSONDecodeError:
            st.error(f"Error reading {SETTINGS_FILE}. Using default settings.")
            return DEFAULT_SETTINGS
    else:
        # Create the file with default settings on first load
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS


def save_settings(new_settings):
    """Writes the current settings dictionary to the JSON file."""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(new_settings, f, indent=4)
        return True
    except IOError as e:
        st.error(f"Could not save settings to {SETTINGS_FILE}: {e}")
        return False
