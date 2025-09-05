# -*- coding: utf-8 -*-

import os
import sys
import re

START_OFFSET = 0x54
DIR_LENGTH = 0x38
FILE_LENGTH = 0x3C

def is_valid_name(byte_name):
    try:
        decoded_name = byte_name.decode("utf-8")
    except UnicodeDecodeError:
        return False
    
    # as file name
    invalid_chars_pattern = r'[\x00-\x1F\x7F\\/:*?"<>|]'
    if re.search(invalid_chars_pattern, decoded_name):
        return False
    
    if len(decoded_name) < 3 or len(decoded_name) > 255:
        return False
    
    return True

def extract(rc1_content, offset, output_dir, dir_length, file_length):
    name_end = rc1_content.find(b"\x00", offset)
    
    if is_valid_name(rc1_content[offset:name_end]):
        file_name = rc1_content[offset:name_end].decode("utf-8")
    else:
        print(f"Ending offset: {hex(offset)} ({rc1_content[offset:offset+8]})")
        return -1
    
    next_name_start = offset + dir_length
    next_name_end = rc1_content.find(b"\x00", next_name_start)
    if is_valid_name(rc1_content[next_name_start:next_name_end]):
        print(f"{hex(offset)}: {file_name} (dir)")
        return next_name_start
    else:
        output_start = int.from_bytes(rc1_content[offset+file_length-8:offset+file_length-4], "little")
        output_size = int.from_bytes(rc1_content[offset+file_length-4:offset+file_length], "little")
        output_end = output_start + output_size
        print(f"{hex(offset)}: {file_name} (file) (offset: {hex(output_start)}, size: {hex(output_size)})")
        
        if output_start > 0: 
            output_content = rc1_content[output_start:output_end]
        else:
            output_content = b""
        
        output_path = os.path.join(output_dir, file_name)
        
        while os.path.isfile(output_path):
            dirname = os.path.dirname(output_path)
            filename = os.path.basename(output_path)
            if filename.find(".") != -1:
                output_path = os.path.join(dirname, filename.replace(".", "_."))
            else:
                output_path = output_path + "_"
        
        with open(output_path, "wb") as file:
            file.write(output_content)
        
            
        next_name_start = offset+file_length-4
        next_name_end = rc1_content.find(b"\x00", next_name_start)
        
        for i in range(300):
            next_name_start += 4
            next_name_end = rc1_content.find(b"\x00", next_name_start)
            if is_valid_name(rc1_content[next_name_start:next_name_end]):
                return next_name_start

        return offset + file_length

def main(rc1_content, start_offset, dir_length, file_length):
    output_dir = os.path.join(os.path.dirname(sys.argv[1]), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    offset = start_offset
    while True:
        if offset == -1: return
        offset = extract(rc1_content, offset, output_dir, dir_length, file_length)

if __name__ == "__main__":
    for file_path in sys.argv[1:]:
        print("Start")
        with open(file_path, "rb") as file:
            rc1_content = file.read()
        main(rc1_content, START_OFFSET, DIR_LENGTH, FILE_LENGTH)
        print("End")