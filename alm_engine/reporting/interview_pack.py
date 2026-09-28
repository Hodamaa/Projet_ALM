from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def build_interview_pack(
    output_zip: str | Path,
    files_to_include: list[str | Path],
) -> Path:
    output = Path(output_zip)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as zf:
        for file_path in files_to_include:
            src = Path(file_path)
            if src.exists() and src.is_file():
                zf.write(src, arcname=src.name)
    return output

