import argparse
from pathlib import Path
import os
import re
import shutil

parser = argparse.ArgumentParser(description="")
parser.add_argument("db_dir", help=r"READWRITE2/DB")
parser.add_argument("database", help="DFATR.BIN")
parser.add_argument("out_dir", default=None)
args = parser.parse_args()


input_dir = Path(args.db_dir)
with open(args.database, "rb") as inf:
    db = inf.read()
out_dir = Path(args.out_dir or os.path.join(args.db_dir, "renamed"))
os.makedirs(out_dir, exist_ok=True)

TRANSLATION_TABLE = str.maketrans({
    "\\": "＼",
    "/": "／",
    ":": "：",
    "*": "＊",
    "?": "？",
    '"': "”",
    "<": "＜",
    ">": "＞",
    "|": "｜",
})

def sanitize_filename(filename: str) -> str:
    sanitized = filename.translate(TRANSLATION_TABLE)

    sanitized = "".join(
        " " if ord(c) < 32 else c
        for c in sanitized
    )

    if not sanitized:
        sanitized = "untitled"

    return sanitized


def get_available_path(path):
    path = Path(path)

    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    i = 2
    while True:
        new_path = parent / f"{stem} ({i}){suffix}"
        if not new_path.exists():
            return new_path
        i += 1

db_info = {}
NAME_START = 0x6A
EXT_START = 0x92
META_SIZE = 0xA0

database = bytearray()
for off in range(0, len(db), 0x4000):
    database +=  db[off : off + 0x3FC0]

for i, off in enumerate(range(0, len(database), META_SIZE)):
    meta = database[off : off + META_SIZE]
    if (name_end := meta.find(b"\x00", NAME_START)) in [-1, 0]:
        continue
    name = meta[NAME_START :  name_end].decode("cp932", errors="ignore")

    if (ext_end := meta.find(b"\x00", EXT_START)) in [-1, 0]:
        continue
    ext = meta[EXT_START :  ext_end].decode("ascii", errors="ignore")

    filesize = int.from_bytes(meta[:4], "little")

    db_info[i] = [name, ext, filesize]


for p in input_dir.iterdir():
    if re.search("^[0-9A-F]+$", p.stem) is None:
        continue

    file_id = int(p.stem, 16)
    if (tmp := db_info.get(file_id)) is None:
        continue
    else:
        name, ext, filesize = tmp

    name = sanitize_filename(name)
    ext = ext.lower() 

    dest = get_available_path(out_dir / f"{name}.{ext}")

    if os.path.getsize(p) == filesize:
        try:
            shutil.copy2(p, dest)
        except OSError as e :
            print(e, dest)
    else:
        print("wrong filesize: id", hex(file_id), "expected", filesize, "but", hex(os.path.getsize(p)))
        try:
            shutil.copy2(p, out_dir / p.stem)
        except OSError as e :
            print(e, dest)

