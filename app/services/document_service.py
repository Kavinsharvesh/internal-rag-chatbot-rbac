import csv
from pathlib import Path
from typing import List, Dict, Any
from app.services.rbac_service import get_permitted_folders

# Base path to resources/data directory
BASE_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "resources" / "data"


def load_documents_for_role(role: str) -> List[Dict[str, Any]]:
    """
    Safely loads documents (.md, .txt, .csv) from resources/data/
    strictly matching the folders permitted for the user's role.
    Returns a list of document objects containing filename, folder, content, and file type.
    """
    permitted_folders = get_permitted_folders(role)
    loaded_docs: List[Dict[str, Any]] = []

    if not BASE_DATA_DIR.exists():
        return loaded_docs

    for folder_name in permitted_folders:
        folder_path = BASE_DATA_DIR / folder_name
        if not folder_path.exists() or not folder_path.is_dir():
            continue

        for file_path in folder_path.iterdir():
            if not file_path.is_file():
                continue

            ext = file_path.suffix.lower()
            relative_name = f"{folder_name}/{file_path.name}"

            if ext in [".md", ".txt"]:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    loaded_docs.append({
                        "filename": relative_name,
                        "folder": folder_name,
                        "content": content,
                        "type": ext[1:]
                    })
                except Exception:
                    continue

            elif ext == ".csv":
                try:
                    row_lines: List[str] = []
                    with open(file_path, mode="r", encoding="utf-8", errors="ignore") as f:
                        reader = csv.DictReader(f)
                        for idx, row in enumerate(reader, start=1):
                            row_str = ", ".join(f"{k}: {v}" for k, v in row.items() if v)
                            row_lines.append(f"Row {idx}: {row_str}")

                    loaded_docs.append({
                        "filename": relative_name,
                        "folder": folder_name,
                        "content": "\n".join(row_lines),
                        "type": "csv"
                    })
                except Exception:
                    continue

    return loaded_docs
