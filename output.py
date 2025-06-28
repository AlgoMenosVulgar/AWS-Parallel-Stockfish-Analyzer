import os
import pandas as pd
from typing import List, Dict, Any


def results_to_dataframe(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Converts a list of result dictionaries into a pandas DataFrame.
    """
    return pd.DataFrame(results)

def save_dataframe(df: pd.DataFrame, output_path: str) -> None:
    """
    Saves the DataFrame to CSV or Excel, appending to an existing file if present.
    """
    ext = os.path.splitext(output_path)[1].lower()
    if ext == '.csv':
        if os.path.exists(output_path):
            df.to_csv(output_path, mode='a', header=False, index=False)
        else:
            df.to_csv(output_path, index=False)
    elif ext in ('.xls', '.xlsx'):
        if os.path.exists(output_path):
            existing = pd.read_excel(output_path)
            combined = pd.concat([existing, df], ignore_index=True)
            combined.to_excel(output_path, index=False)
        else:
            df.to_excel(output_path, index=False)
    else:
        raise ValueError(f"Unsupported file extension for saving: {ext}")
