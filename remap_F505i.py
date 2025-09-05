import sys
import re
import os

def main():
    with open(sys.argv[1], "rb") as inf:
        data = inf.read()
    with open(re.sub(r"\.bin$", ".oob", sys.argv[1]), "rb") as inf:
        oob = inf.read()

    output = sys.argv[1] + "_fat.bin"

    assert len(data) % 512 == 0
    assert len(oob) % 16 == 0
    assert (len(oob) // 16) * 512 == len(data)

    data_sector_size = 0x200
    oob_sector_size = 0x10

    
    
    chunk_dicts = []
    matched = set()
    for block in range(len(oob)//oob_sector_size):
        sector_data = data[block * data_sector_size : (block+1) * data_sector_size]
        sector_oob = oob[block * oob_sector_size : (block+1) * oob_sector_size]

        if sector_oob[4:6] != b"\xFE\xFF": continue

        sector_id = int.from_bytes(sector_oob[0x6:0xA], "big")
        if sector_id == 0xFF_FF_FF_FF: continue


        if sector_id in matched:
            print(f"WARN: duplicate block id (Block id: {hex(sector_id)}, OOB offset: {hex(block * oob_sector_size)})")

        chunk_dicts.append({"sector_id": sector_id, "sector_data": sector_data})
        matched.add(sector_id)
        

    
    sorted_dicts = sorted(chunk_dicts, key=lambda x:x["sector_id"])
    fat = bytearray((sorted_dicts[-1]["sector_id"]+1) * data_sector_size)
    for chunk_dict in sorted_dicts:
        print(hex(chunk_dict["sector_id"]))
        fat[chunk_dict["sector_id"] * data_sector_size : 
            (chunk_dict["sector_id"]+1) * data_sector_size] = chunk_dict["sector_data"]
        
            
    with open(output, "wb") as outf:
        outf.write(fat)

if __name__ == "__main__":
    main()