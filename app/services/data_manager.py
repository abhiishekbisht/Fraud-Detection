import pandas as pd
import os
from typing import Dict

class DataManager:
    """Manages datasets in memory for the backend services with disk persistence fallback."""
    def __init__(self):
        self._datasets: Dict[str, pd.DataFrame] = {}
        self.raw_dir = "data/raw"
        self.cleaned_dir = "data/cleaned"

    def register_dataset(self, dataset_id: str, df: pd.DataFrame) -> None:
        """
        Registers a dataset DataFrame with the given ID.
        """
        self._datasets[dataset_id] = df

    def get_dataset(self, dataset_id: str) -> pd.DataFrame:
        """
        Retrieves a registered dataset DataFrame by its ID.
        If not in memory, falls back to loading from:
        1. data/cleaned/{dataset_id}.csv (cleaned version)
        2. data/raw/{dataset_id}.csv (raw version)
        Raises KeyError if not found.
        """
        if dataset_id not in self._datasets:
            cleaned_path = os.path.join(self.cleaned_dir, f"{dataset_id}.csv")
            raw_path = os.path.join(self.raw_dir, f"{dataset_id}.csv")
            
            target_path = None
            if os.path.exists(cleaned_path):
                target_path = cleaned_path
            elif os.path.exists(raw_path):
                target_path = raw_path
                
            if target_path:
                try:
                    df = pd.read_csv(target_path)
                    self._datasets[dataset_id] = df
                except Exception as e:
                    raise KeyError(f"Dataset '{dataset_id}' found at {target_path} but failed to read: {str(e)}")
            else:
                raise KeyError(f"Dataset '{dataset_id}' not found.")
        return self._datasets[dataset_id]

    def delete_dataset(self, dataset_id: str) -> None:
        """
        Deletes a dataset from the manager (both in-memory and from disk - raw and cleaned).
        """
        if dataset_id in self._datasets:
            del self._datasets[dataset_id]
            
        # Clean up files on disk
        for directory in [self.raw_dir, self.cleaned_dir]:
            path = os.path.join(directory, f"{dataset_id}.csv")
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

# Singleton instance for application-wide use
data_manager = DataManager()
