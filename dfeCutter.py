import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

possible_start_address_list = [0x0, 0x24, 0x48, 0x50, 0x54, 0x200, 0x2F0] 

file_write_lock = Lock()


def detect_start_address(file_path, possible_start_address_list, magics):
    magic_sizes = [len(magic) for magic in magics]
    
    with open(file_path, "rb") as file:
        file_data = file.read(possible_start_address_list[-1] + 0x10)
        file_size = len(file_data)
    
    for possible_start_address in possible_start_address_list:
        if file_size < (possible_start_address + 0x10):
            continue

        for magic, magic_size in zip(magics, magic_sizes):
            if file_data[possible_start_address:possible_start_address+magic_size] == magic:
                return possible_start_address
    
    return None


def process_file(input_path, start_address, output_dir):
    file_name = os.path.basename(input_path)
    output_path = os.path.join(output_dir, file_name)

    try:
        with open(input_path, "rb") as inf:
            file_data = inf.read()

            if file_data[0:1] == b"/":
                try:
                    file_data.decode("utf-8")
                    return f"Ignored: {file_name} (Symbolic Link)"
                except:
                    pass

            if len(file_data) <= start_address:
                return f"Ignored: {file_name} (Empty)"

            # Change the file name if it is duplicated.
            with file_write_lock:
                base, ext = os.path.splitext(output_path)
                count = 1
                while os.path.exists(output_path):
                    output_path = f"{base} ({count}){ext}"
                    count += 1

                with open(output_path, "wb") as outf:
                    outf.write(file_data[start_address:])

        return f"Processed: {file_name}"
    except Exception as e:
        return f"Error: {file_name} ({e})"


def main(dfe_dir, possible_start_address_list):
    output_dir = os.path.join(os.path.dirname(dfe_dir), "output_dfe")
    
    input_paths = []

    for root, _, files in os.walk(dfe_dir):
        for file in files:
            input_paths.append(os.path.join(root, file))

    if len(input_paths) == 0:
        raise ValueError("no file")
    
    print("Looking for the start address...")
    start_address = None
    
    for input_path in input_paths:
        if start_address != None: break
        
        if input_path.lower().endswith(".gif"):
            start_address = detect_start_address(input_path, possible_start_address_list, [b"GIF89a", b"GIF87a"])
            
        elif input_path.lower().endswith(".mld"):
            start_address = detect_start_address(input_path, possible_start_address_list, [b"melo"])

        elif input_path.lower().endswith(".jpg") or input_path.lower().endswith(".jpeg"):
            start_address = detect_start_address(
                input_path,
                possible_start_address_list,
                [
                    b"\xFF\xD8\xFF\xDB", 
                    b"\xFF\xD8\xFF\xE0\x00\x10\x4A\x46\x49\x46\x00\x01",
                    b"\xFF\xD8\xFF\xEE",
                    b"\xFF\xD8\xFF\xE1",
                    b"\xFF\xD8\xFF\xE0"
                ]
            )
    
        elif input_path.lower().endswith(".cfd"):
            start_address = detect_start_address(input_path, possible_start_address_list, [b"CFD"])
        
        elif input_path.lower().endswith(".swf"):
            start_address = detect_start_address(input_path, possible_start_address_list, [b"FWS", b"CWS"])
    
    if start_address == None:
        raise Exception("Failed: The start address could not be found.")
    
    print(f"Start Address: {hex(start_address)} ({input_path})")

    os.makedirs(output_dir, exist_ok=True)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_file, path, start_address, output_dir) for path in input_paths]
        for future in as_completed(futures):
            print(future.result())
            
    print(f"Succeeded => {output_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python dfeCutter.py dfe_directory")
    else:
        dfe_dir = sys.argv[1]
        main(dfe_dir, possible_start_address_list)
