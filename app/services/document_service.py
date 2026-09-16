import csv
from pathlib import Path
from typing import List, Dict, Any
from app.services.rbac_service import get_permitted_folders

# Base path to resources/data directory
BASE_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "resources" / "data"

# Sensitive fields to exclude from chunks to minimize exposure
SENSITIVE_FIELDS = {"salary"}


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    """
    Chunks text into character blocks of size ~chunk_size with overlap.
    Splits on paragraph/line boundaries where possible.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []

    current_chunk = ""
    for para in paragraphs:
        if len(para) > chunk_size:
            lines = [line.strip() for line in para.split("\n") if line.strip()]
            for line in lines:
                if len(current_chunk) + len(line) + 1 > chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = current_chunk[-overlap:] + "\n" + line if overlap < len(current_chunk) else line
                else:
                    current_chunk = (current_chunk + "\n" + line).strip() if current_chunk else line
        else:
            if len(current_chunk) + len(para) + 2 > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = current_chunk[-overlap:] + "\n\n" + para if overlap < len(current_chunk) else para
            else:
                current_chunk = (current_chunk + "\n\n" + para).strip() if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks if chunks else [text[:chunk_size]]


def load_all_chunks() -> List[Dict[str, Any]]:
    """
    Phase 2B Document Processor:
    Loads and chunks ALL documents from resources/data/ for vector indexing.
    Attaches metadata to every chunk:
      - department: e.g. "engineering", "finance", "general", "hr", "marketing"
      - source: e.g. "engineering/engineering_master_doc.md"
      - filename: e.g. "engineering_master_doc.md"
      - chunk_id: e.g. "engineering/engineering_master_doc.md_chunk_0"
    Excludes sensitive HR fields (salary) from chunk representations.
    """
    all_chunks: List[Dict[str, Any]] = []

    if not BASE_DATA_DIR.exists():
        return all_chunks

    for dept_folder in BASE_DATA_DIR.iterdir():
        if not dept_folder.is_dir():
            continue

        department = dept_folder.name.lower()

        for file_path in dept_folder.iterdir():
            if not file_path.is_file():
                continue

            ext = file_path.suffix.lower()
            relative_source = f"{department}/{file_path.name}"
            filename = file_path.name

            if ext in [".md", ".txt"]:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    text_chunks = chunk_text(content, chunk_size=400, overlap=50)

                    for idx, chunk_str in enumerate(text_chunks):
                        chunk_id = f"{relative_source}_chunk_{idx}"
                        all_chunks.append({
                            "chunk_id": chunk_id,
                            "content": chunk_str,
                            "metadata": {
                                "department": department,
                                "source": relative_source,
                                "filename": filename,
                                "chunk_id": chunk_id
                            }
                        })
                except Exception:
                    continue

            elif ext == ".csv":
                try:
                    with open(file_path, mode="r", encoding="utf-8", errors="ignore") as f:
                        reader = csv.DictReader(f)
                        for idx, row in enumerate(reader, start=0):
                            filtered_items = [
                                f"{k}: {v}" for k, v in row.items()
                                if k.lower() not in SENSITIVE_FIELDS and v
                            ]
                            row_str = f"Employee Record: {', '.join(filtered_items)}"
                            chunk_id = f"{relative_source}_row_{idx}"

                            all_chunks.append({
                                "chunk_id": chunk_id,
                                "content": row_str,
                                "metadata": {
                                    "department": department,
                                    "source": relative_source,
                                    "filename": filename,
                                    "chunk_id": chunk_id
                                }
                            })
                except Exception:
                    continue

    return all_chunks


def load_documents_for_role(role: str) -> List[Dict[str, Any]]:
    """
    Preserved Phase 1 document loader:
    Safely loads document objects matching permitted folders for the given role.
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
                            filtered_items = [
                                f"{k}: {v}" for k, v in row.items()
                                if k.lower() not in SENSITIVE_FIELDS and v
                            ]
                            row_str = ", ".join(filtered_items)
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
