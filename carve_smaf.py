import os
import argparse
from pathlib import Path
import re
import sys

DEBUG = False
CRC_SIZE = 2
DEFALUT_TITLE = "NO NAME"

CNTI_CODE_MAP = {
    0x00: "cp932",
    0x01: "iso-8859-1",
    0x02: "euc-kr",
    0x03: "hz-gb-2312",
    0x04: "big5",
    0x05: "koi8-r",
    # python doesn't support
    # 0x06: "tcvn-5773:1993",
    0x20: "utf-16-be",
    0x21: "utf-32-be",
    0x22: "utf-7",
    0x23: "utf-8",
    0x24: "utf-16-be",
    0x25: "utf-32-be",
}

OPDA_CODE_MAP = {
    0x00: "cp932",
    0x01: "iso-8859-1",
    0x02: "iso-2022-kr",
    0x03: "hz-gb-2312",
    0x04: "big5",
    0x05: "koi8-r",
    # python doesn't support
    # 0x06: "tcvn-5773:1993",
    0x20: "utf-16-be",
    0x21: "utf-32-be",
    0x22: "utf-7",
    0x23: "utf-8",
    0x24: "utf-16-be",
    0x25: "utf-32-be",
}



def sanitize_filename(filename):
    filename = "".join(ch for ch in filename if ch >= " " and ch != "\x7f")
    mapping = {
        '\\': '＼', '/': '／', ':': '：', '*': '＊', '?': '？',
        '"': '＂', '<': '＜', '>': '＞', '|': '｜'
    }
    for char, replacement in mapping.items():
        filename = filename.replace(char, replacement)
    return filename.strip()


def get_song_title_strict(smaf_dict):
    title = DEFALUT_TITLE

    if b"OPDA" in smaf_dict:
        for dchs in smaf_dict[b"OPDA"]:
            if b"Dch" in dchs:
                encoding = OPDA_CODE_MAP.get(dchs["opda_code_type"], 'utf-8')
                if b"ST" in dchs[b"Dch"]:
                    title = dchs[b"Dch"][b"ST"].decode(encoding, errors="replace")
                    break

    if b"CNTI" in smaf_dict and b"ST" in smaf_dict[b"CNTI"]["option"]:
        encoding = CNTI_CODE_MAP.get(smaf_dict[b"CNTI"]["contents_code_type"], 'utf-8')
        title = smaf_dict[b"CNTI"]["option"][b"ST"].decode(encoding, errors="replace")

    return sanitize_filename(title)


def parse_cnti_option(data):
    res = {}
    i = 0
    chunk = bytearray()
    key = None
    value = None
    
    while i < len(data):
        b = data[i : i + 1]

        if b == b":":
            key = bytes(chunk)
            chunk = bytearray()
            i += 1
            continue

        if b == b',':
            value = bytes(chunk)
            if key is not None:
                res[key] = value
                key = None
                value = None

            chunk = bytearray()
            i += 1
            continue

        if b == b'\\':
            if i + 1 < len(data):
                nxt = data[i+1 : i+2]

                if nxt == b',':
                    chunk += b','
                elif nxt == b":":
                    chunk += b":"
                elif nxt == b'\\':
                    chunk += b'\\'
                else:
                    chunk += nxt

                i += 2
            else:
                i += 1

            continue

        chunk += b
        i += 1

    return res


def parse_smaf(smaf_data):
    smaf_dict = {}
    pos = 8
    smaf_size = len(smaf_data) - CRC_SIZE
    while True:
        if pos == smaf_size:
            break
        elif pos + 8 > smaf_size:
            raise ValueError(f"Chunk parsing failed, pos: {hex(pos)}")

        chunk_id = smaf_data[pos : pos + 4]
    
        chunk_size = int.from_bytes(smaf_data[pos + 4 : pos + 8], "big")
        if pos + 8 + chunk_size > smaf_size:
            raise ValueError(f"Chunk parsing failed, pos: {hex(pos)}")

        chunk_data = smaf_data[pos + 8 : pos + 8 + chunk_size]

        if DEBUG:
            print(f"{chunk_id}: {chunk_size}")

        if chunk_id == b"OPDA":
            opda_dicts = []
            opda_pos = 0
            while True:
                if opda_pos == chunk_size:
                    break
                elif opda_pos + 8 > chunk_size:
                    raise ValueError(f"Chunk parsing failed, pos: {hex(pos)}")

                opda_id = chunk_data[opda_pos : opda_pos + 3]
                opda_code_type = chunk_data[opda_pos + 3]
                opda_size = int.from_bytes(chunk_data[opda_pos + 4 : opda_pos + 8], "big")
                if opda_pos + 8 + opda_size > chunk_size:
                    raise ValueError(f"Chunk parsing failed, pos: {hex(pos + opda_pos)}")
                
                if DEBUG:
                    print(f"  {opda_id}: {opda_size}")

                dch_data = chunk_data[opda_pos + 8 : opda_pos +  8 + opda_size]
                
                if opda_id == b"Dch":
                    sub_pos = 0
                    sub_dict = {}

                    while True:
                        if sub_pos == opda_size:
                            break
                        elif sub_pos + 4 > opda_size:
                            raise ValueError(f"Chunk parsing failed, pos: {hex(pos + opda_pos + sub_pos)}")
                        
                        sub_id = dch_data[sub_pos : sub_pos + 2]
                        sub_size = int.from_bytes(dch_data[sub_pos + 2 : sub_pos + 4], "big")
                        sub_data = dch_data[sub_pos + 4 : sub_pos + 4 + sub_size]
                        sub_dict[sub_id] = sub_data

                        if DEBUG:
                            print(f"    {sub_id}: {sub_size}, {sub_data}")

                        sub_pos += 4 + sub_size

                    opda_dicts.append({
                        opda_id: sub_dict,
                        "opda_code_type": opda_code_type,
                    })

                else:
                    opda_dicts.append({
                        opda_id: dch_data,
                        "opda_code_type": opda_code_type,
                    })
                if DEBUG:
                    print(f"    opda_code_type: {opda_code_type}")
                opda_pos += 8 + opda_size

            smaf_dict[chunk_id] = opda_dicts
        elif chunk_id == b"CNTI":
            cnti_dict = {
                "contents_class": chunk_data[0],
                "contents_type": chunk_data[1],
                "contents_code_type": chunk_data[2],
                "copy_status": chunk_data[3],
                "copy_counts": chunk_data[4],
                "option": {},
            }

            if chunk_size > 5:
                option_data = chunk_data[5:]
                options = parse_cnti_option(option_data)
                for k, v in options.items():
                    cnti_dict["option"][k] =  v

            if DEBUG:
                for k, v in cnti_dict.items():
                    print(f"  {k}: {v}")

            smaf_dict[chunk_id] = cnti_dict
        else:
            smaf_dict[chunk_id] = chunk_data

        pos += 8 + chunk_size
    return smaf_dict


def extract_smaf(file_path, output_dir, use_numbering, add_offset, strict_mode):
    with open(file_path, 'rb') as f:
        data = f.read()

    pos = 0
    extracted_count = 0
    file_infos = []
    
    while True:
        pos = data.find(b'MMMD', pos)
        if pos == -1:
            break
        print(f"Found offset: {hex(pos)}")
        
        size = int.from_bytes(data[pos + 4 : pos + 8], 'big')
        smaf_data = data[pos : pos + 8 + size]

        if strict_mode:
            try:
                smaf_dict = parse_smaf(smaf_data)
            except Exception as e:
                print(f" => Broken SMAF file so skipped: {e}")
                pos += 1
                continue
            
        if strict_mode:
            is_phrase = True if b"MMMG" in smaf_dict else False
            title = get_song_title_strict(smaf_dict)
            ext = '.spf' if is_phrase else '.mmf'
        else:
            is_phrase = True if b"MMMG" in smaf_data else False
            title = DEFALUT_TITLE
            ext = '.spf' if is_phrase else '.mmf'

        file_infos.append([title, ext, smaf_data, pos])
        print(f" => {title}{ext}")
        extracted_count += 1
        pos += 8 + size
            
    num_digits = len(str(extracted_count))
    song_count = 0
    for file_info in file_infos:
        title, ext, smaf_data, pos = file_info
        
        numbering = f"{song_count:0{num_digits}d} " if use_numbering else ""
        hex_digit = len(hex(len(data))[2:])
        offset = f"0x{pos:0{hex_digit}X}_" if add_offset else ""
        filename = f"{numbering}{offset}{title}"

        duplicate_counter = 2
        original_filename = filename
        while os.path.exists(os.path.join(output_dir, filename + ext)):
            filename = f"{original_filename} ({duplicate_counter})"
            duplicate_counter += 1
                
        with open(os.path.join(output_dir, filename + ext), 'wb') as out_f:
            out_f.write(smaf_data)
        
        song_count += 1
        
def main():
    parser = argparse.ArgumentParser(description="Carve SMAF from binary")
    parser.add_argument("inputs", nargs="+", help="Input files or folders")
    parser.add_argument("-o", "--output", help="Output directory")
    parser.add_argument("-n", "--numbering", action="store_true", help="Use numbering to filename")
    parser.add_argument("-ao", "--add-offset", action="store_true", help="Add offset to filename")
    parser.add_argument("-ns", "--no-strict", action="store_true", help="It does not verify the contents; it simply cuts out the amount of data indicated by the size field in the header.")
    
    args = parser.parse_args()
    
    files = []
    for path in args.inputs:
        if os.path.isdir(path):
            files.extend(Path(path).rglob('*'))
        else:
            files.append(Path(path))
            
    files = [f for f in files if f.is_file()]

    first = Path(args.inputs[0])
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = first.parent / "SMAF_carved"
    
    if len(files) > 0:
        for file_path in files:
            print(f"\nInput: {file_path.name}")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            extract_smaf(file_path, output_dir, args.numbering, args.add_offset, not args.no_strict)
        print(f"\noutput dir => {output_dir}")
    else:
        print("No input file")
    
    

if __name__ == "__main__":
    main()
