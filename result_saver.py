import glob
import os

import pandas as pd


class ResultSaver:
    def __init__(self, overwrite_results: bool = False):
        self.output_file_name = "results.xlsx"
        self.overwrite_results = overwrite_results

    def save_results(self, output_dir: str) -> pd.DataFrame:
        combined_results = self.combine_results_from_all_subdirectories(output_dir)
        combined_results_filename = self.save(combined_results, output_dir)
        print(
            f"Combined results from all files in {output_dir} saved at: {combined_results_filename}"
        )
        return combined_results

    def results_exist(self, output_dir: str) -> bool:
        results_path = os.path.join(output_dir, self.output_file_name)
        return os.path.exists(results_path) and os.path.getsize(results_path) > 0

    def save(self, categorized_df: pd.DataFrame, output_dir: str) -> str:
        """
        Saves a pandas df to an Excel file.

        Parameters:
            categorized_df (pd.DataFrame): The pandas df.
        Returns:
            str: File path to the saved Excel file.
        """
        os.makedirs(output_dir, exist_ok=True)

        # Define the file name with a timestamp
        excel_file_path = os.path.join(output_dir, self.output_file_name)
        categorized_df.to_excel(excel_file_path, index=False)

        # Note that this is really just for debugging - I think eventually we can use only Excel
        csv_file_path = os.path.join(output_dir, "results.csv")
        categorized_df.to_csv(csv_file_path, index=False)
        return excel_file_path

    def results_exist_and_should_be_kept(self, results_directory: str):
        """
        True if the results already exist in the specified directory and they should
        not be overwritten.
        """
        return not self.overwrite_results and self.results_exist(results_directory)

    def combine_results_from_all_subdirectories(
        self, parent_directory: str
    ) -> pd.DataFrame:
        all_results_files = glob.glob(
            f"{parent_directory}/*/**/{self.output_file_name}", recursive=True
        )
        return pd.concat(
            [pd.read_excel(file) for file in all_results_files], ignore_index=True
        )
