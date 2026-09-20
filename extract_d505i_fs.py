import sys
from pathlib import Path
import os
import argparse

CONFIGS = {
    "D505i":[
        {
            "main_category": 0x95,
            "sub_category": 0x00,
            "ext": "adf",
            "start": 0xC,
            "out_dir": "JAVA", 
        },
        {
            "main_category": 0x95,
            "sub_category": 0x4E,
            "ext": "scr",
            "out_dir": "JAVA", 
        },
        {
            "main_category": 0x95,
            "sub_category": 0x27,
            "ext": "jar",
            "out_dir": "JAVA", 
        },
        {
            "main_category": 0x95,
            "sub_category": 0x9C,
            "ext": "sdf",
            "out_dir": "JAVA", 
        },
        {
            "main_category": 0x15,
            "sub_category": 0x09,
            "ext": "html",
            "out_dir": "HTML", 
        },
        {
            "main_category": 0x4A,
            "sub_category": 0x50,
            "ext": "mld",
            "out_dir": "RINGTONE", 
        },
        {
            "main_category": 0x4A,
            "sub_category": 0x48,
            "ext": "mld",
            "out_dir": "RINGTONE", 
        },
        {
            "main_category": 0x62,
            "sub_category": 0x00,
            "ext": "jpg",
            "out_dir": "IMAGE", 
        },
        {
            "main_category": 0x47,
            "sub_category": 0x80,
            "ext": None,
            "out_dir": "IMAGE", 
        },
    ],
}

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

parser = argparse.ArgumentParser(description="")
parser.add_argument("input")
parser.add_argument("-o", "--out-dir", default=None)
args = parser.parse_args()

input_file = Path(args.input)
with open(input_file, "rb") as inf:
    fs_data = inf.read()
base_out_dir = Path(args.out_dir or os.path.join(input_file.parent, "extracted"))
os.makedirs(base_out_dir, exist_ok=True)


file_config = CONFIGS["D505i"]

for off in range(0, len(fs_data), 0x200):
    if (
        fs_data[off : off + 1] == b"\x40"
        and fs_data[off + 6: off + 8] == b"\x77\x44"
    ):
        main = int.from_bytes(fs_data[off + 1 : off + 3], "big")
        sub =  int.from_bytes(fs_data[off + 3 : off + 5], "big")
        id = fs_data[off + 5]
        size = int.from_bytes(fs_data[off + 0x8 : off + 0xC], "big")
        print(hex(main), hex(sub), hex(id), fs_data[off + 0xC : off + 0x10], hex(off), size)

        file_data = fs_data[off + 0xC : off + 0xC + size]
        file_type = next(filter(lambda x: x["main_category"] == main and x["sub_category"] == sub, file_config), None)

        if file_type:
            out_dir = base_out_dir / file_type["out_dir"]

            if file_type["out_dir"] == "JAVA":
                file_name = f"{id & 0xF:03}.{file_type['ext']}"
            elif file_type["out_dir"] == "RINGTONE":
                name_len = file_data[0x7]
                name = file_data[0x8 : 0x8 + name_len].decode("cp932")
                file_name = f"{name}.{file_type['ext']}"
                file_data = file_data[0x3C:]
            elif file_type["out_dir"] == "IMAGE" and file_type["ext"] is None:
                name_end = file_data.find(b"\x00", 0x8)
                file_name = file_data[0x8 : name_end].decode("cp932")
                file_data = file_data[0x44:]
            elif file_type["out_dir"] == "IMAGE" and file_type["ext"] == "jpg":
                name_end = file_data.find(b"\x00", 0x14)
                file_name = file_data[0x14 : name_end].decode("cp932") + "." + file_type['ext']
                file_data = file_data[0x4C:]
            else:
                file_name = f"{id:05}.{file_type['ext']}"
        else:
            out_dir = base_out_dir / "OTHER"
            file_name = f"{main:05}_{sub:05}_{id:05}.bin"

        os.makedirs(out_dir, exist_ok=True)
        file_name = sanitize_filename(file_name)
        out_path = get_available_path(out_dir / file_name)

        print(file_name)
        with open(out_path, "wb") as outf:
            outf.write(file_data)

