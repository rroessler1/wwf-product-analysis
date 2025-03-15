import io
import os
import zipfile

from abc import ABC, abstractmethod


class Downloader(ABC):

    @abstractmethod
    def download(self, directory: str):
        """Downloads the data into the given directory"""


class StreamlitDownloader(Downloader):
    """Downloads Zipfile from Streamlit UI"""

    def __init__(self, uploaded_file):
        self.uploaded_file = uploaded_file

    def download(self, directory):
        with zipfile.ZipFile(io.BytesIO(self.uploaded_file.read()), "r") as zf:
            os.makedirs(directory, exist_ok=True)
            zf.extractall(directory)


class NoopDownloader(Downloader):
    """Does nothing, assumes data is already there"""

    def download(self, directory):
        pass
