#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_and_extract_SH900i_media.py

Usage:
    python scan_and_extract_SH900i_media.py /path/to/input_root /path/to/output_root

Behavior:
  - Copies all extensionless files in <input_root>/MML/MLD to <output_root>/MLD_files,
    appending ".mld" to each copied file.
  - Copies all extensionless files in <input_root>/MML/AFD to <output_root>/AFD_files,
    appending ".afd" to each copied file.

Notes:
  - Only files with no extension (Path.suffix == "") are targeted.
  - If the output file name already exists, a sequential suffix (_1, _2, …) is added
    to avoid overwriting existing files.
"""

from pathlib import Path
import argparse
import sys
import shutil


def has_no_extension(p: Path) -> bool:
    # Consider the file as extensionless if Path.suffix is an empty string
    return p.is_file() and p.suffix == ""


def make_unique_dest(dest: Path) -> Path:
    """
    Return the same path if it does not exist.
    If it already exists, append a sequential suffix like
    basename_1.ext, basename_2.ext, ... until an unused name is found.
    Assumes dest includes a file extension.
    """
    if not dest.exists():
        return dest

    parent = dest.parent
    stem = dest.stem  # Base filename without extension
    suffix = dest.suffix  # Example: .mld
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def extract_and_rename(src_dir: Path, out_dir: Path, add_ext: str) -> int:
    """
    src_dir: Input directory (e.g., <input_root>/MML/MLD)
    out_dir: Output directory (e.g., <output_root>/MLD_files)
    add_ext: Extension to be appended (e.g., ".mld")
    Returns: Number of files successfully copied
    """
    count = 0
    if not src_dir.exists() or not src_dir.is_dir():
        print(f"Warning: source dir not found: {src_dir}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)

    for entry in sorted(src_dir.iterdir()):
        if has_no_extension(entry):
            dest_name = entry.name + add_ext
            dest_path = out_dir / dest_name
            dest_path = make_unique_dest(dest_path)
            # Binary copy (do not preserve metadata)
            try:
                with entry.open("rb") as fsrc, dest_path.open("wb") as fdst:
                    shutil.copyfileobj(fsrc, fdst)
                print(f"Copied: {entry} -> {dest_path}")
                count += 1
            except Exception as e:
                print(f"Error copying {entry} -> {dest_path}: {e}")
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Extract extensionless files from MML/MLD and MML/AFD and append .mld/.afd"
    )
    parser.add_argument("input_root", type=str, help="Input root folder (e.g. path to SH900i dump root)")
    parser.add_argument("output_root", type=str, help="Output folder where MLD_files and AFD_files will be created")
    args = parser.parse_args()

    input_root = Path(args.input_root).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()

    if not input_root.exists() or not input_root.is_dir():
        print(f"Error: input_root does not exist or is not a directory: {input_root}")
        sys.exit(1)

    # Look for MML/MLD and MML/AFD under the specified input root
    mml_mld = input_root / "MML" / "MLD"
    mml_afd = input_root / "MML" / "AFD"

    out_mld_dir = output_root / "MLD_files"
    out_afd_dir = output_root / "AFD_files"

    print(f"Input root:  {input_root}")
    print(f"Output root: {output_root}")
    print()

    mld_count = extract_and_rename(mml_mld, out_mld_dir, ".mld")
    afd_count = extract_and_rename(mml_afd, out_afd_dir, ".afd")

    print()
    print("Done.")
    print(f"MLD files copied: {mld_count}")
    print(f"AFD files copied: {afd_count}")


if __name__ == "__main__":
    main()
