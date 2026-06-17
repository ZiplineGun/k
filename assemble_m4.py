import argparse
import os

PRINT_FS = None
RENAME = True # vodafone
PRINT_FILE_ID = None # vodafone

TYPE_DEF = {
    "jar": 512,
    "rms": 1024,
    "ico": 768,
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
        data[:4] == b"\xff\xd8\xff\xe0"
            and data[6:0xA] == b"JFIF"
        or data[:4] == b"\xff\xd8\xff\xe1"
            and data[6:0xA] == b"Exif"
        or data[:4] == b"\xFF\xD8\xFF\xDB"
        or data[:4] == b"\xFF\xD8\xFF\xEE"
       ):
        return "jpg"
    elif data[:4] == b"\x89PNG":
        return "png"
    elif data[:4] == b"melo":
        return "mld"
    elif data.find(b".jam") != -1:
        return "adf"
    elif data[:4] == b"MMMD":
        return "mmf"
    
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
                            "metadata": metadata,
                            "meta_off": block_number+off,
                        })

                    off += 0x10
            block_data = inf.read(0x20000)
            block_number += 0x20000
        return vspace
    

def filter_vspace(vspace):
    filtterd_vspace = {}
    rest_vspace = {}

    for fs, chunk_infos in vspace.items():
        for chunk_info in chunk_infos:
            if (chunk_info["marker"] == 0xFC and chunk_info["flag"] != 1 
                and not any(f["chunk_id"] == chunk_info["chunk_id"] for f in filtterd_vspace.get(fs, []))
            ):
                filtterd_vspace.setdefault(fs, []).append(chunk_info)
            else:
                rest_vspace.setdefault(fs, []).append(chunk_info)

    return filtterd_vspace, rest_vspace


if __name__ == "__main__":
    print("Start")

    parser = argparse.ArgumentParser(description="Keitai M4 Assemble")
    parser.add_argument("input")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("-e","--detect-extension", action=argparse.BooleanOptionalAction, help="Adds an extension by detecting the file type from its magic number. Misclassification is possible.")
    parser.add_argument("-v","--V601N-mode", action=argparse.BooleanOptionalAction, help="Strip the 4-byte header at the start of the file and rename base on matadata file.")
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
        f"{os.path.basename(args.input)}_output"
    )
    os.makedirs(out_dir, exist_ok=True)

    filtered_vspace = get_vspace(args.input)
    if len(filtered_vspace) == 0:
        raise ValueError("No valid M4 blocks were found.")
    
    filtered_vspace, rest_vspace = filter_vspace(filtered_vspace)

    file_infos = {}
    for fs, chunk_infos in filtered_vspace.items():
        file_data = bytearray()
        
        for chunk_info in sorted(chunk_infos, key=lambda x: x["chunk_id"]):
            file_data += chunk_info["chunk"]

        if args.V601N_mode:
            file_genre = int.from_bytes(file_data[:2], "little")
            file_id = int.from_bytes(file_data[2:4], "little")

            if file_genre == 256 or file_genre in TYPE_DEF.values():
                file_data = file_data[4:]
            ext = detect_extension(file_data) if args.detect_extension else "bin"
            out_name = f"region_{file_genre:02d}_{file_id:02d}_{fs:05d}.{ext}"

            file_infos[fs] = {
                "file_genre": file_genre,
                "file_id": file_id,
                "file_name": out_name,
            }
        else:
            ext = detect_extension(file_data) if args.detect_extension else "bin"
            out_name = f"region_{fs:05d}.{ext}"
        
        with open(os.path.join(out_dir, out_name), "wb") as outf:
            outf.write(file_data)


    if args.undelete:
        for fs, chunk_infos in rest_vspace.items():
            for chunk_info in chunk_infos:
                file_data = chunk_info["chunk"]

                ext = detect_extension(file_data) if args.detect_extension else "bin"
                out_name = f"region_{fs:05d}_{chunk_info['chunk_id']:02d}_recovered.{ext}"

                cnt = 2
                while os.path.isfile(os.path.join(out_dir, out_name)):
                    out_name = f"region_{fs:05d}_{chunk_info['chunk_id']:02d}_recovered ({cnt}).{ext}"
                    cnt += 1
                
                with open(os.path.join(out_dir, out_name), "wb") as outf:
                    outf.write(file_data)
                    if int.from_bytes(file_data[:2], "little") == 256 and int.from_bytes(file_data[2:4], "little") == PRINT_FILE_ID:
                        print(out_name, " ".join([f"{b:02X}" for b in chunk_info["metadata"]]), hex(chunk_info["meta_off"]))

    # rename base on table file
    if RENAME and args.V601N_mode:
        with open(os.path.join(out_dir, file_infos[6]["file_name"]), "rb") as inf:
            filetable = inf.read()
            
        with open(os.path.join(out_dir, file_infos[262]["file_name"]), "rb") as inf:
            filetable += inf.read()
            
        with open(os.path.join(out_dir, file_infos[518]["file_name"]), "rb") as inf:
            filetable += inf.read()
        

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
                if info["file_genre"] == 256 and info["file_id"] == i
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
            elif do_warning:
                print(f"WARN: skipped {filename}, file_id={i}")
            
                
        #with open(os.path.join(out_dir, file_infos[6150]["file_name"]), "rb") as inf:
        #    app_table = inf.read()
        

        for jad in sorted([f for f in os.listdir(out_dir) if os.path.isfile(os.path.join(out_dir, f)) and f.endswith(".jad")]):
            jad_id = int(jad[2 : 8])

            for ext, genre_id in TYPE_DEF.items():
                target_info = [
                    info
                    for info in file_infos.values()
                    if info["file_genre"] == genre_id and info["file_id"] == id
                ]
                
                if len(target_info) > 0:
                    src_path = os.path.join(out_dir, target_info[0]["file_name"])
                    os.rename(
                        src_path,
                        os.path.join(out_dir, f"JA{jad_id:06}.{ext}")
                    )

    print("End")
