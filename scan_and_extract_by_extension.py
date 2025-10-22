#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Any

SEARCH_WINDOW = 0x1000  # window size for searching magic starting at declared start
COPY_BUFFER_SIZE = 16 * 1024  # 16 KiB

# ---------------------------------------------------------------------------
# Configure file type definitions here.
# ---------------------------------------------------------------------------

DOCOMO_FILE_TYPES: List[Dict[str, Any]] = [
    {
        "extension": [".mid", ".midi"],
        "magic": [
            {"magic": b"MThd", "start": 0},
        ],
    },
    {
        "extension": [".swf", ".mht"],
        "magic": [
            {"magic": b"FWS", "start": 0},
        ],
    },
    {
        "extension": [".swf", ".mht"],
        "magic": [
            {"magic": b"CWS", "start": 0},
        ],
    },
    {
        "extension": [".3gp", ".mp4", ".m4a"],
        "magic": [
            {"magic": b"ftyp", "start": 4},
        ],
    },
    {
        "extension": [".zbf"],
        "magic": [
            {"magic": b"ZVFA", "start": 0},
        ],
    },
    {
        "extension": [".gif"],
        "magic": [
            {"magic": b"GIF87a", "start": 0},
        ],
    },
    {
        "extension": [".gif"],
        "magic": [
            {"magic": b"GIF89a", "start": 0},
        ],
    },
    {
        "extension": [".bmp"],
        "magic": [
            {"magic": b"BM", "start": 0},
        ],
    },
    {
        "extension": [".mld", ".mel"],
        "magic": [
            {"magic": b"melo", "start": 0},
        ],
    },
    {
        "extension": [".cfd"],
        "magic": [
            {"magic": b"CFD", "start": 0},
        ],
    },
    {
        "extension": [".afd"],
        "magic": [
            {"magic": b"CFD", "start": 0},
        ],
    },
    {
        "extension": [".vui"],
        "magic": [
            {"magic": b"DVUI", "start": 0},
        ],
    },
    {
        "extension": [".ucp"],
        "magic": [
            {"magic": b"PK\x03\x04", "start": 0},
        ],
    },
    {
        "extension": [".ucm"],
        "magic": [
            {"magic": b"DM", "start": 0},
        ],
    },
]

SOFTBANK_FILE_TYPES: List[Dict[str, Any]] = [
    {
        "extension": [".mid", ".midi"],
        "magic": [
            {"magic": b"MThd", "start": 0},
        ],
    },
    {
        "extension": [".swf", ".mht"],
        "magic": [
            {"magic": b"FWS", "start": 0},
        ],
    },
    {
        "extension": [".swf", ".mht"],
        "magic": [
            {"magic": b"CWS", "start": 0},
        ],
    },
    {
        "extension": [".3gp", ".mp4", ".m4a"],
        "magic": [
            {"magic": b"ftyp", "start": 4},
        ],
    },
    {
        "extension": [".zbf"],
        "magic": [
            {"magic": b"ZVFA", "start": 0},
        ],
    },
    {
        "extension": [".gif"],
        "magic": [
            {"magic": b"GIF87a", "start": 0},
        ],
    },
    {
        "extension": [".gif"],
        "magic": [
            {"magic": b"GIF89a", "start": 0},
        ],
    },
    {
        "extension": [".bmp"],
        "magic": [
            {"magic": b"BM", "start": 0},
        ],
    },
    {
        "extension": [".mmf", ".non", ".huf"], # .non is on V501SH, .huf is on V604SH
        "magic": [
            {"magic": b"MMMD", "start": 0},
        ],
    },
    {
        "extension": [".xcsf"], # kisekae
        "magic": [
            None,
        ],
    },
]

KDDI_FILE_TYPES: List[Dict[str, Any]] = [
    {
        "extension": [".mid", ".midi"],
        "magic": [
            {"magic": b"MThd", "start": 0},
        ],
    },
    {
        "extension": [".3gp", ".mp4", ".m4a", ".3g2"],
        "magic": [
            {"magic": b"ftyp", "start": 4},
        ],
    },
    {
        "extension": [".zbf"],
        "magic": [
            {"magic": b"ZVFA", "start": 0},
        ],
    },
    {
        "extension": [".gif"],
        "magic": [
            {"magic": b"GIF87a", "start": 0},
        ],
    },
    {
        "extension": [".gif"],
        "magic": [
            {"magic": b"GIF89a", "start": 0},
        ],
    },
    {
        "extension": [".bmp"],
        "magic": [
            {"magic": b"BM", "start": 0},
        ],
    },
    {
        "extension": [".mmf", ".non", ".huf"],
        "magic": [
            {"magic": b"MMMD", "start": 0},
        ],
    },
    {
        "extension": [".dxm"],
        "magic": [
            {"magic": b"MCDF", "start": 0},
        ],
    },
    {
        "extension": [".swf", ".mht", ".kmmf"],
        "magic": [
            {"magic": b"FWS", "start": 0},
        ],
    },
    {
        "extension": [".swf", ".mht", ".kmmf"],
        "magic": [
            {"magic": b"CWS", "start": 0},
        ],
    },
]

WILLCOM_FILE_TYPES: List[Dict[str, Any]] = [
    {
        "extension": [".mid", ".midi"],
        "magic": [
            {"magic": b"MThd", "start": 0},
        ],
    },
    {
        "extension": [".3gp", ".mp4", ".m4a"],
        "magic": [
            {"magic": b"ftyp", "start": 4},
        ],
    },
    {
        "extension": [".zbf"],
        "magic": [
            {"magic": b"ZVFA", "start": 0},
        ],
    },
    {
        "extension": [".gif"],
        "magic": [
            {"magic": b"GIF87a", "start": 0},
        ],
    },
    {
        "extension": [".gif"],
        "magic": [
            {"magic": b"GIF89a", "start": 0},
        ],
    },
    {
        "extension": [".bmp"],
        "magic": [
            {"magic": b"BM", "start": 0},
        ],
    },
    {
        "extension": [".mmf", ".non", ".huf"],
        "magic": [
            {"magic": b"MMMD", "start": 0},
        ],
    },
    {
        "extension": [".dxm"],
        "magic": [
            {"magic": b"MCDF", "start": 0},
        ],
    },
    {
        "extension": [".swf", ".mht", ".kmmf"],
        "magic": [
            {"magic": b"FWS", "start": 0},
        ],
    },
    {
        "extension": [".swf", ".mht", ".kmmf"],
        "magic": [
            {"magic": b"CWS", "start": 0},
        ],
    },
]

# ---------------------------------------------------------------------------
# Helper & validation
# ---------------------------------------------------------------------------

logger = logging.getLogger("scan_extract")


def normalize_extensions(exts: Sequence[str]) -> List[str]:
    """Return normalized extensions starting with a dot and lowercased."""
    out: List[str] = []
    for e in exts:
        s = str(e)
        if not s.startswith('.'):
            s = '.' + s
        out.append(s.lower())
    return out


def validate_and_normalize_file_types(file_types: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate entries and normalize extensions and magic entries.

    Accepts magic==None to mean 'match by extension only'.
    """
    out: List[Dict[str, Any]] = []
    for entry in file_types:
        if "extension" not in entry:
            raise ValueError("Each FILE_TYPES entry must contain 'extension' key")
        extensions = normalize_extensions(entry["extension"])
        magic = entry.get("magic", None)
        if magic is None:
            norm_magic = None
        else:
            # must be a sequence (list) of dicts
            if not isinstance(magic, Sequence):
                raise TypeError("'magic' must be a sequence of dicts or None")
            norm_magic = []
            for m in magic:
                if not isinstance(m, dict):
                    raise TypeError("each magic entry must be a dict")
                mg = m.get("magic", None)
                if not isinstance(mg, (bytes, bytearray)):
                    raise TypeError("magic must be bytes, e.g. b'MThd'")
                start = int(m.get("start", 0))
                norm_magic.append({"magic": bytes(mg), "start": start})
        out.append({"extension": extensions, "magic": norm_magic})
    return out


# Validate and normalize file type definitions at startup
DOCOMO_FILE_TYPES = validate_and_normalize_file_types(DOCOMO_FILE_TYPES)
SOFTBANK_FILE_TYPES = validate_and_normalize_file_types(SOFTBANK_FILE_TYPES)
KDDI_FILE_TYPES = validate_and_normalize_file_types(KDDI_FILE_TYPES)
WILLCOM_FILE_TYPES = validate_and_normalize_file_types(WILLCOM_FILE_TYPES)


def build_ext_map(file_types: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Map extension -> list of file-type dicts for quick lookup."""
    ext_map: Dict[str, List[Dict[str, Any]]] = {}
    for fmt in file_types:
        for ext in fmt["extension"]:
            ext_map.setdefault(ext, []).append(fmt)
    return ext_map


def iter_files(root: Path) -> List[Path]:
    """Collect files recursively. Returns a list (ok for ~3k files)."""
    return [p for p in root.rglob("*") if p.is_file()]


# ---------------------------------------------------------------------------
# Magic detection and extraction computation
# ---------------------------------------------------------------------------

def read_head(path: Path, nbytes: int) -> bytes:
    with path.open('rb') as f:
        return f.read(nbytes)


def find_magic_positions(head: bytes, magics: Optional[Sequence[Dict[str, Any]]]) -> Optional[List[int]]:
    """Search for each magic inside its allowed search window.

    If magics is None => treat as extension-only match and return an empty list
    (meaning 'match' but no positions to align).

    Returns a list of positions corresponding to magics if all found; otherwise
    returns None.
    """
    if magics is None:
        return []  # matched by extension only

    hl = len(head)
    positions: List[int] = []
    for m in magics:
        magic: bytes = m["magic"]
        start: int = int(m["start"])
        mlen = len(magic)
        window_start = start
        window_end = start + SEARCH_WINDOW
        if hl < window_start + mlen:
            return None
        max_search_pos = min(window_end, hl - mlen)
        pos = head.find(magic, window_start, max_search_pos + mlen)
        if pos == -1 or not (window_start <= pos <= max_search_pos):
            return None
        positions.append(pos)
    return positions


def compute_extract_start(positions: List[int], starts: List[int]) -> int:
    """Compute an extract_start such that (found_pos - extract_start) == declared start.

    If positions is empty (i.e. magic==None), return 0.
    """
    if not positions:
        return 0
    candidates = [p - s for p, s in zip(positions, starts)]
    if all(c == candidates[0] for c in candidates):
        return candidates[0]
    return min(candidates)


# ---------------------------------------------------------------------------
# Output naming utilities
# ---------------------------------------------------------------------------

def ensure_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def make_unique_filename(dest_dir: Path, name: str) -> Path:
    """Return a filesystem-safe path that does not overwrite existing files.

    Uses the "name (2).ext" convention to avoid collisions.
    """
    candidate = dest_dir / name
    if not candidate.exists():
        return candidate
    stem = Path(name).stem
    suffix = Path(name).suffix
    i = 2
    while True:
        new_name = f"{stem} ({i}){suffix}"
        candidate = dest_dir / new_name
        if not candidate.exists():
            return candidate
        i += 1


# ---------------------------------------------------------------------------
# Core file processing
# ---------------------------------------------------------------------------

def write_from_offset(src: Path, dst: Path, offset: int) -> None:
    """Write bytes from src starting at offset to dst. offset may be negative,
    which causes left-padding with NUL bytes.
    """
    if offset >= 0:
        with src.open('rb') as sf, dst.open('wb') as df:
            sf.seek(offset)
            shutil.copyfileobj(sf, df, length=COPY_BUFFER_SIZE)
    else:
        pad = -offset
        with dst.open('wb') as df, src.open('rb') as sf:
            df.write(b'\x00' * pad)
            shutil.copyfileobj(sf, df, length=COPY_BUFFER_SIZE)


def copy_whole_file(src: Path, dst: Path) -> None:
    shutil.copy2(src, dst)


def process_file(
    src: Path,
    output_root: Path,
    file_types_for_ext: List[Dict[str, Any]],
    all_file_types: List[Dict[str, Any]],
    scan_all_magics: bool,
    extract: bool,
    dry_run: bool,
    lock,
    counters: Dict[str, int],
) -> None:
    """Process a single file: detect magic, compute extraction and write output.

    file_types_for_ext: formats directly mapped from extension
    all_file_types: entire chosen_types list (for --scan-magics)
    scan_all_magics: whether to include all magic-bearing formats for detection
    """
    with lock:
        counters['total'] += 1

    # Build candidate list:
    candidates: List[Dict[str, Any]] = list(file_types_for_ext)  # copy
    if scan_all_magics:
        # Add formats from all_file_types that have magic != None and are not already present.
        for fmt in all_file_types:
            if fmt.get('magic') is None:
                continue
            if fmt not in candidates:
                candidates.append(fmt)

    if not candidates:
        logger.debug("no candidate formats for %s (ext=%s)", src, src.suffix)
        return

    # determine maximum header size required to check any candidate format
    max_head = 0
    for fmt in candidates:
        if fmt.get('magic') is None:
            max_head = max(max_head, SEARCH_WINDOW + 16)
        else:
            max_head = max(max_head, max((m['start'] + SEARCH_WINDOW + len(m['magic']) for m in fmt['magic']), default=0))
    if max_head <= 0:
        max_head = SEARCH_WINDOW + 16

    try:
        head = read_head(src, max_head)
    except Exception as exc:
        logger.warning("failed to read head of %s: %s", src, exc)
        return

    chosen_fmt: Optional[Dict[str, Any]] = None
    computed_extract_start: Optional[int] = None

    # Try candidates in order (prefer extension-mapped ones first because
    # file_types_for_ext was seeded first)
    for fmt in candidates:
        if fmt.get('magic') is None:
            positions = []
        else:
            positions = find_magic_positions(head, fmt['magic'])
        if positions is None:
            continue
        starts = [int(m['start']) for m in (fmt['magic'] or [])]
        extract_start = compute_extract_start(positions, starts)
        chosen_fmt = fmt
        computed_extract_start = extract_start
        break

    if chosen_fmt is None:
        logger.debug("no magic match: %s", src)
        return

    # Determine canonical output extension and folder (use extension[0])
    ext0 = chosen_fmt['extension'][0].lstrip('.')
    out_folder = output_root / f"{ext0.upper()}_files"
    out_name = f"{src.stem}.{ext0}"

    # Choose unique destination path under lock to avoid race.
    with lock:
        ensure_folder(out_folder)
        dest_path = make_unique_filename(out_folder, out_name)
        counters['matched'] += 1

    if dry_run:
        if extract:
            try:
                size = src.stat().st_size
                es = computed_extract_start if computed_extract_start is not None else 0
                if es >= 0:
                    written = max(0, size - es)
                    pad = 0
                else:
                    written = size
                    pad = -es
                logger.info("[DRY] %s -> %s, pad=%d, write_from=%d, written=%d bytes", src, dest_path, pad, max(0, es), pad + written)
            except Exception:
                logger.info("[DRY] %s -> %s (cannot stat source)", src, dest_path)
        else:
            logger.info("[DRY] copy %s -> %s", src, dest_path)
        return

    # Perform actual write
    try:
        if extract:
            assert computed_extract_start is not None
            write_from_offset(src, dest_path, computed_extract_start)
            try:
                st = src.stat()
                os.utime(dest_path, (st.st_atime, st.st_mtime))
            except Exception:
                logger.debug("failed to preserve mtime for %s", dest_path)
            logger.debug("extracted: %s -> %s (extract_start=%d)", src, dest_path, computed_extract_start)
        else:
            copy_whole_file(src, dest_path)
            logger.debug("copied: %s -> %s", src, dest_path)
    except Exception as exc:
        logger.error("failed to write %s: %s", dest_path, exc)


# ---------------------------------------------------------------------------
# CLI / Orchestration
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scan directory for files by extension+magic and copy or extract into extension-based folders.")
    p.add_argument('input', help='Input directory')
    p.add_argument('output', help='Output directory')
    p.add_argument('--extract', action='store_true', help='Extract from computed offset so magic is aligned to declared start')
    p.add_argument('--dry-run', action='store_true', help='Do not write files, only show what would happen')
    p.add_argument('--workers', type=int, default=16, help='Number of parallel worker threads')
    p.add_argument('-v', '--verbose', action='store_true', help='Verbose logging')
    p.add_argument('-p', '--profile', choices=['docomo', 'softbank', 'kddi', 'willcom', 'both'], default='docomo',
                   help="Which FILE_TYPES profile to use: 'docomo' (default)")
    p.add_argument('--scan-only-magics', action='store_true',
                   help="Regardless of file extension, search all FILE_TYPES entries for magic bytes and, on match, treat file as that type.")
    p.add_argument('--search-window', default=None,
                   help="Search window size (decimal or hex like 0x1000). Overrides default SEARCH_WINDOW.")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s %(levelname)s: %(message)s')

    # Parse and apply search-window if provided
    global SEARCH_WINDOW
    if args.search_window is not None:
        s = str(args.search_window).strip()
        try:
            # int(s, 0) accepts 0x... hex or decimal
            SEARCH_WINDOW = int(s, 0)
        except Exception as exc:
            raise SystemExit(f"invalid --search-window value: {s} ({exc})")

    input_root = Path(args.input).resolve()
    output_root = Path(args.output).resolve()
    if not input_root.is_dir():
        raise SystemExit(f"input directory not found: {input_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    # Select file type sets based on profile
    if args.profile == 'docomo':
        chosen_types = DOCOMO_FILE_TYPES
    elif args.profile == 'softbank':
        chosen_types = SOFTBANK_FILE_TYPES
    elif chosen_types == 'kddi':
        chosen_types = KDDI_FILE_TYPES
    elif args.profile == 'willcom':
        chosen_types = WILLCOM_FILE_TYPES
    else:
        # both
        chosen_types = DOCOMO_FILE_TYPES + SOFTBANK_FILE_TYPES + KDDI_FILE_TYPES + WILLCOM_FILE_TYPES

    ext_map = build_ext_map(chosen_types)
    files = iter_files(input_root)
    logger.info("found %d files to consider (SEARCH_WINDOW=%d, scan_magics=%s)", len(files), SEARCH_WINDOW, args.scan_only_magics)

    counters = {"total": 0, "matched": 0}
    lock = ThreadLock()

    workers = max(1, args.workers)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [
            ex.submit(
                process_file,
                f,
                output_root,
                ext_map.get(f.suffix.lower(), []),
                chosen_types,
                args.scan_only_magics,
                args.extract,
                args.dry_run,
                lock,
                counters
            ) for f in files
        ]
        for fut in as_completed(futures):
            exc = fut.exception()
            if exc:
                logger.exception("worker exception: %s", exc)

    logger.info("scanned %d files, matched %d files", counters['total'], counters['matched'])


# Simple cross-platform thread lock wrapper so type is clear
class ThreadLock:
    def __init__(self):
        from threading import Lock
        self._lock = Lock()

    def __enter__(self):
        self._lock.acquire()

    def __exit__(self, exc_type, exc, tb):
        self._lock.release()

    # context-manager style lock usage for 'with lock:'


if __name__ == '__main__':
    main()
