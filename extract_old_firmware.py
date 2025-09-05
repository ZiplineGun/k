import os
import sys
import struct

def find_adf(bytes, start_offset=0):
    adf_start_offset = start_offset - 1
    
    while True:
        adf_start_offset = bytes.find(b"\x14\x00", adf_start_offset+1)
        if adf_start_offset == -1: break
        if bytes[adf_start_offset+0x03] != 0x00: continue
        if bytes[adf_start_offset+0x0E] != 0x1A: continue
        if bytes[adf_start_offset+0x10:adf_start_offset+0x30] != b"\x00"*0x20: continue
        try:
            appname_start_offset = adf_start_offset+0x6C
            appname_end_offset = bytes.find(b"\x00", appname_start_offset)
            print(bytes[appname_start_offset:appname_end_offset].decode("cp932"), hex(adf_start_offset))
        except:
            continue
        break
    
    return adf_start_offset

def main(path):
    output_dir = os.path.join(os.path.dirname(sys.argv[1]), "output")
    
    output_adf_dir = os.path.join(output_dir, "ADF")
    os.makedirs(output_adf_dir, exist_ok=True)
    
    output_sp_dir = os.path.join(output_dir, "SP")
    os.makedirs(output_sp_dir, exist_ok=True)
    
    output_jar_dir = os.path.join(output_dir, "JAR")
    os.makedirs(output_jar_dir, exist_ok=True)

    with open(path, "rb") as file:
        firmware = file.read()
        
    id = 0
    start_offset = 0
    while True:
        adf_address = find_adf(firmware, start_offset)
        if adf_address == -1: break
        
        adf_end = firmware.find(b"\x00"*0x21, adf_address+0x6C) + 0x21
        adf_content = firmware[adf_address:adf_end]
        
        sp_size = int.from_bytes(firmware[adf_address+0x5C:adf_address+0x5F], byteorder="little")
        sp_address = adf_end
        sp_end = sp_address + sp_size
        sp_content = firmware[sp_address:sp_end]
        
        jar_size = int.from_bytes(firmware[adf_address+0x58:adf_address+0x5B], byteorder="little")
        jar_address = sp_end
        jar_end = jar_address + jar_size
        jar_content = firmware[jar_address:jar_end]
        
        with open(os.path.join(output_adf_dir, f"ADF{id}"), "wb") as file:
            file.write(adf_content)
        
        with open(os.path.join(output_sp_dir, f"SP{id}"), "wb") as file:
            file.write(sp_content)
        
        with open(os.path.join(output_jar_dir, f"JAR{id}"), "wb") as file:
            file.write(jar_content)
            
        print(f"Success!")
        
        start_offset = jar_end
        id += 1

if __name__ == "__main__":
    main(sys.argv[1])