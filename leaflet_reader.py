# leaflet_processing/leaflet_reader.py

import glob
import os
from typing import List

from natsort import natsorted
import pypdfium2 as pdfium
from PyPDF2 import PdfReader

from file_downloaders import Downloader


class LeafletReader:

    def __init__(self, file_downloader: Downloader):
        """
        Parameters:
            file_downloader (Downloader): Responsible for downloading the files
        """
        self.file_downloader = file_downloader

    def download_leaflets(self, pdf_dir: str) -> None:
        """
        Saves the leaflets into the pdf_dir.
        """
        os.makedirs(pdf_dir, exist_ok=True)
        self.file_downloader.download(pdf_dir)
        print("Leaflets downloaded successfully.")

    def convert_pdf_to_images(
        self, pdf_path, output_dir: str, overwrite_images=False
    ) -> List[str]:
        """
        Splits a PDF into individual images.

        Parameters:
            pdf_path (str): Path to the PDF file.
            output_dir (str): Path to where the images will be written.
            overwrite_images (bool): If False, skips the conversion to images, if enough images are found.

        Returns:
            List[str]: List of image paths.
        """
        if not overwrite_images:
            # Note: Streamlit would require: reader = PdfReader(io.BytesIO(pdf_path.read()))
            reader = PdfReader(pdf_path)
            png_files = glob.glob(f"{output_dir}/*.png")
            png_files = [os.path.basename(f) for f in png_files]
            pdf_name, _ = os.path.splitext(os.path.basename(pdf_path))

            expected_image_names = set(
                [f"{pdf_name}_{i + 1}.png" for i in range(len(reader.pages))]
            )
            if len(expected_image_names - set(png_files)) == 0:
                print(
                    f"Found PNG images for {pdf_path}. Skipping conversion from PDF to images."
                )
                return natsorted(png_files)

        print(f"Converting {pdf_path} to images.")
        os.makedirs(output_dir, exist_ok=True)

        pdf_doc = pdfium.PdfDocument(pdf_path)
        paths = []

        for i, page in enumerate(pdf_doc):
            image = page.render(scale=4).to_pil()
            output_filename = os.path.join(output_dir, f"{pdf_name}_{i + 1}.png")
            image.save(output_filename, format="PNG")
            paths.append(output_filename)

        return natsorted(paths)
