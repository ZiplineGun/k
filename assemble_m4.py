import argparse
import os
import re

PRINT_FS = None
RENAME = True # vodafone
PRINT_FILE_ID = None # vodafone

V601N_TYPE_DEF = {
    "jar": 512,
    "rms": 1024,
    "ico": 768,
}

MOVA_TYPE_DEF =  {
    "N504i": {
        "html": {
            "genre": [1],
            "name_start": None,
            "file_start": 0x0,
            "dir_name": "HTML_CHACHE",
        },
        "image": {
            "genre": [3],
            "name_start": 0x4,
            "file_start": 0x18,
            "dir_name": "IMAGE",
        },
        "mld": {
            "genre": [4],
            "name_start": 0x2,
            "file_start": 0x36,
            "dir_name": "RINGTONE",
        },
        "jar": {
            "genre": [7],
            "name_start": None,
            "file_start": 0x0,
            "dir_name": "JAVA",
        },
        "scr": {
            "genre": [8],
            "name_start": None,
            "file_start": 0x0,
            "dir_name": "JAVA",
        },
        "adf": {
            "genre": [9],
            "name_start": None,
            "file_start": 0x0,
            "dir_name": "JAVA",
        },
    },
    "N506i": {
        "jar": {
            "genre": [31],
            "name_start": None,
            "file_start": 0x0,
            "dir_name": "JAVA",
        },
        "scr": {
            "genre": [32],
            "name_start": None,
            "file_start": 0x0,
            "dir_name": "JAVA",
        },
        "adf": {
            "genre": [33],
            "name_start": None,
            "file_start": 0x0,
            "dir_name": "JAVA",
        },
        "image": {
            "genre": [37, 39, 42, 43],
            "name_start": None,
            "file_start": 0x0,
            "dir_name": "IMAGE",
        },
        "mld": {
            "genre": [38],
            "name_start": None,
            "file_start": 0x0,
            "dir_name": "RINGTONE",
        },
        "html": {
            "genre": [50],
            "name_start": None,
            "file_start": 0x0,
            "dir_name": "HTML_CHACHE",
        },
        "3gp": {
            "genre": [81],
            "name_start": None,
            "file_start": 0x0,
            "dir_name": "VIDEO",
        },
    },
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


def detect_extension(data):
    if data[:4] == b"\x50\x4B\x03\x04":
        return "jar"
    elif (
        data[:2] == b"\xff\xd8"
            and data[-2:] == b"\xff\xd9"
       ):
        return "jpg"
    elif data[:4] == b"\x89PNG":
        return "png"
    elif data[:6] in [b"GIF87a", b"GIF89a"]:
        return "gif"
    elif data[:4] == b"melo":
        return "mld"
    elif data.find(b".jam") != -1:
        return "adf"
    elif data[:4] == b"MMMD":
        return "mmf"
    elif data[:6] in [b"<html>", b"<HTML>"]:
        return "html"
    elif data[:3] in [b"CWS", b"FWS", b"ZWS"]:
        return "swf"
    elif data[4:8] == b"ftyp":
        return "3gp"
    
    if data.find(b"MIDlet-Name:") != -1:
        try:
             data.decode("UTF-8")
             return "jad"
        except UnicodeDecodeError:
            pass
        
    return "bin"


def get_vspace(input_path):
    vspace = {}

    with open(input_path, "rb") as inf:
        block_data = inf.read(0x20000)
        block_number = 0

        while len(block_data) > 0:
            if block_data[0x1FFFA:0x1FFFE] == b"\x55\x55\xFF\xFF":
                #print("\n")
                #print(" ".join([f"{byte:0=2X}" for byte in data[0x1FFE0:0x1FFF0]]))
                #print(" ".join([f"{byte:0=2X}" for byte in data[0x1FFF0:0x20000]]))
                off = 0
                while (metadata := block_data[off : off + 0x10]) != b"\xFF" * 0x10:
                    marker = metadata[1]
                    chunk_id = metadata[2]
                    fs = int.from_bytes(metadata[3 : 6], "little")
                    loc = int.from_bytes(metadata[8 : 0xA], "little")
                    size = int.from_bytes(metadata[0xC : 0x10], "little")
                    flag = int.from_bytes(metadata[0x6 : 0x8], "little")

                    chunk = block_data[
                        0x1FFE0 - (loc * 0x80) : 0x1FFE0 - (loc * 0x80) + size
                    ]

                    if fs == PRINT_FS:
                        print(
                            f"{block_number+off:07X}" + ":"
                            , " ".join([f"{byte:0=2X}" for byte in metadata]) 
                            , f"(chunk_id={hex(chunk_id)}, {size=}, flag={flag:04X})"
                        )
                        dir = os.path.join(out_dir, "chunk")
                        os.makedirs(dir, exist_ok=True)
                        with open(os.path.join(dir, f"{fs}_{hex(block_number + off)}_{chunk_id}_{flag}.bin"), "wb") as outf:
                            outf.write(chunk)

                    if (0x1FFE0 - (loc * 0x80) + size) <= 0x1FFE0:
                        vspace.setdefault(fs, []).append({
                            "marker": marker,
                            "chunk_id": chunk_id,
                            "flag": flag,
                            "chunk": chunk,
                            "size": size,
                            "metadata": metadata,
                            "meta_off": block_number+off,
                        })

                    off += 0x10
            block_data = inf.read(0x20000)
            block_number += 0x20000
        return vspace

def filter_vspace(vspace):
    filterd_vspace = {}
    rest_vspace = {}

    for fs, chunk_infos in vspace.items():
        for chunk_info in chunk_infos:

            if (chunk_info["marker"] == 0xFC and chunk_info["flag"] != 1 
            ):
                filterd_vspace.setdefault(fs, []).append(chunk_info)
            else:
                rest_vspace.setdefault(fs, []).append(chunk_info)

    return filterd_vspace, rest_vspace

# def filter_vspace(vspace):
#     filterd_vspace = {}
#     rest_vspace = {}

#     max_info = {}
#     for fs, chunk_infos in vspace.items():
#         for chunk_info in chunk_infos:

#             if (chunk_info["marker"] == 0xFC and chunk_info["flag"] != 1 
#                 and chunk_info["flag"] > max_info.get(fs, {}).get(chunk_info["chunk_id"], 0)
#             ):
#                 max_info.setdefault(fs, {})[chunk_info["chunk_id"]] = chunk_info["flag"]

#     for fs, chunk_infos in vspace.items():
#         for chunk_info in chunk_infos:
#             if (chunk_info["marker"] == 0xFC and chunk_info["flag"] == max_info.get(fs, {}).get(chunk_info["chunk_id"])):
#                 filterd_vspace.setdefault(fs, []).append(chunk_info)
#             else:
#                 rest_vspace.setdefault(fs, []).append(chunk_info)

#     return filterd_vspace, rest_vspace


def get_html_title(html_data):
    html = html_data.decode("cp932", errors="ignore")

    m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)

    if m is None or m[1].isspace():
        return None
    else:
        return m[1].strip()


def carve_filename(file_data, start):
    st = start
    ed = file_data.find(b"\x00", st)

    if ed == -1:
        return None

    out_basename = file_data[st : ed].decode("cp932", errors="ignore")

    if out_basename.isspace():
        return None
    else:
        return out_basename


if __name__ == "__main__":
    print("Start")

    parser = argparse.ArgumentParser(description="Keitai M4 Assemble")
    parser.add_argument("input")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("-e","--detect-extension", action=argparse.BooleanOptionalAction, help="Adds an extension by detecting the file type from its magic number. Misclassification is possible.")
    parser.add_argument("-r", "--rename-mode", choices=["V601N", "N504i", "N506i"], help="Rename file using the name obtained from headers or metadata.")
    parser.add_argument("-nw","--no-warning", action="store_true", help="No warning is displayed.")
    parser.add_argument(
        "-u",
        "--undelete",
        help="Undelete unused blocks.",
        action=argparse.BooleanOptionalAction,
    )

    args = parser.parse_args()
    do_warning = not args.no_warning
    out_dir = args.output or os.path.join(
        os.path.dirname(args.input),
        f"{os.path.basename(args.input)}_extracted"
    )

    filtered_vspace = get_vspace(args.input)
    if len(filtered_vspace) == 0:
        raise ValueError("No valid M4 blocks were found.")
    os.makedirs(out_dir, exist_ok=True)
    
    filtered_vspace, rest_vspace = filter_vspace(filtered_vspace)

    file_infos = {}
    for fs, chunk_infos in filtered_vspace.items():
        file_data = bytearray()
        genre = fs & 0x0000FF
        id = (fs & 0xFFFF00) >> 8

        if fs == PRINT_FS:
            print("\n[Selected]")
            for chunk_info in chunk_infos:
                print(
                    f"{chunk_info['meta_off']:07X}" + ":",
                    " ".join([f"{byte:0=2X}" for byte in chunk_info['metadata']]), 
                    f"(chunk_id={hex(chunk_info['chunk_id'])}, size={chunk_info['size']}, flag={chunk_info['flag']})"
                )

        for chunk_info in sorted(chunk_infos, key=lambda x: (x["chunk_id"], -x["flag"])):
            file_data += chunk_info["chunk"]
            if fs == PRINT_FS:
                print(chunk_info["flag"])

        out_basename = None
        ext = None
        parent_dir = None
        if args.rename_mode == "V601N":
            sub_genre = int.from_bytes(file_data[:2], "little")
            sub_id = int.from_bytes(file_data[2:4], "little")

            if sub_genre == 256 or sub_genre in V601N_TYPE_DEF.values():
                file_data = file_data[4:]
            
            if genre == 9:
                ext = "html"
            elif args.detect_extension:
                ext = detect_extension(file_data)
            else:
                ext = "bin"
            
            if ext == "html":
                out_basename = get_html_title(file_data)
            else:
                out_basename = f"region_{genre:03d}_{id:05d}_sub_{sub_genre:03d}_{sub_id:03d}"

            file_infos[fs] = {
                "sub_genre": sub_genre,
                "sub_id": sub_id,
                "file_name": f"{out_basename}.{ext}",
            }
        elif args.rename_mode in ["N504i", "N506i"]:
            type_def = MOVA_TYPE_DEF[args.rename_mode]
            for type, info in type_def.items():
                if genre in info["genre"]:
                    parent_dir = info["dir_name"]

                    if type in ["jar", "scr", "adf"]:
                        out_basename = f"{id:03d}"
                    elif type == "html":
                        out_basename = get_html_title(file_data)
                    elif info["name_start"] is not None and file_data[info["name_start"]] != 0:
                        out_basename = carve_filename(file_data, info["name_start"])

                    file_data = file_data[info["file_start"] :]

                    if type == "image":
                        ext = detect_extension(file_data)
                    else:
                        ext = type

                    break

        if ext is None:
            ext = detect_extension(file_data) if args.detect_extension else "bin"

        if out_basename is None:
            out_basename = f"region_{genre:03d}_{id:05d}"
        else:
            out_basename = sanitize_filename(out_basename)

        if parent_dir is not None:
            out_basename = os.path.join(parent_dir, out_basename)
            os.makedirs(os.path.join(out_dir, parent_dir), exist_ok=True)
    
        # avoid duplicate filename
        cnt = 2
        out_path = os.path.join(out_dir, f"{out_basename}.{ext}")
        while os.path.isfile(out_path):
            out_path = os.path.join(out_dir, f"{out_basename} ({cnt}).{ext}")
            cnt += 1

        with open(out_path, "wb") as outf:
            outf.write(file_data)


    if args.undelete:
        for fs, chunk_infos in rest_vspace.items():
            cnt = 1
            for chunk_info in chunk_infos:
                file_data = chunk_info["chunk"]
                genre = fs & 0x0000FF
                id = (fs & 0xFFFF00) >> 8
                
                ext = detect_extension(file_data) if args.detect_extension else "bin"

                if cnt == 1:
                    out_name = f"region_{genre:03d}_{id:05d}_recovered"
                else:
                    out_name = f"region_{genre:03d}_{id:05d}_recovered ({cnt})"
                cnt += 1

                out_path = os.path.join(out_dir, f"{out_name}.{ext}")
                
                with open(out_path, "wb") as outf:
                    outf.write(file_data)

                    if int.from_bytes(file_data[:2], "little") == 256 and int.from_bytes(file_data[2:4], "little") == PRINT_FILE_ID:
                        print(out_name, " ".join([f"{b:02X}" for b in chunk_info["metadata"]]), hex(chunk_info["meta_off"]))

    # rename base on table file
    if RENAME and args.rename_mode == "V601N":
        with open(os.path.join(out_dir, file_infos[6]["file_name"]), "rb") as inf:
            filetable = inf.read()
            
        with open(os.path.join(out_dir, file_infos[262]["file_name"]), "rb") as inf:
            filetable += inf.read()
            
        with open(os.path.join(out_dir, file_infos[518]["file_name"]), "rb") as inf:
            filetable += inf.read()
        
        jad_paths = []
        for i, off in enumerate(range(0, len(filetable), 0x5C)):
            tbl = filetable[off : off + 0x5C]
            if tbl == b"\x00" * 0x5C:
                break
            
            filesize = int.from_bytes(tbl[:4], "little")
            filename = sanitize_filename(
                tbl[0x13 : tbl.find(b"\x00", 0x13)].decode("cp932")
            )
            target_info = [
                info
                for info in file_infos.values()
                if info["sub_genre"] == 256 and info["sub_id"] == i
            ]
            
            dest_path = os.path.join(out_dir, filename)
            if os.path.isfile(dest_path):
                count = 1
                while os.path.isfile(dest_path):
                    name, ext = os.path.splitext(filename)
                    dest_path = os.path.join(out_dir, f"{name} ({count}){ext}")
                    count += 1
            
            if len(target_info) > 0:
                src_path = os.path.join(out_dir, target_info[0]["file_name"])
                
                if os.path.getsize(src_path) != filesize and do_warning:
                    print(f"WARN: different filesize:{filename}, file_id={i}, assumed={filesize}, actual={os.path.getsize(src_path)}")
                
                os.rename(
                    src_path,
                    dest_path,
                )
                if dest_path[-4:] == ".jad":
                    jad_paths.append(dest_path)
            elif do_warning:
                print(f"WARN: skipped {filename}, file_id={i}")
            
                
        #with open(os.path.join(out_dir, file_infos[6150]["file_name"]), "rb") as inf:
        #    app_table = inf.read()
        

        for jad in jad_paths:
            jad_id = int(
                        re.search(r"JA(\d{6})", os.path.basename(jad))[1]
                     )

            for ext, genre_id in V601N_TYPE_DEF.items():
                target_info = [
                    info
                    for info in file_infos.values()
                    if info["sub_genre"] == genre_id and info["sub_id"] == jad_id
                ]
                
                if len(target_info) > 0:
                    src_path = os.path.join(out_dir, target_info[0]["file_name"])
                    destname = f"JA{jad_id:06}.{ext}"
                    try:
                        os.rename(
                            src_path,
                            os.path.join(out_dir, destname)
                        )
                    except FileExistsError:
                        print(f"Skipped because file already exists: {destname}")

    print("End")
