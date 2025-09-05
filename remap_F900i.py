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


    data_block_size = 0x200 * 0x20
    oob_block_size = 0x10 * 0x20
    
    
    chunk_dicts = []
    matched = set()
    for block in range(len(oob)//oob_block_size):
        data_block = data[block * data_block_size : (block+1) * data_block_size]
        oob_block = oob[block * oob_block_size : (block+1) * oob_block_size]

        if oob_block[6:8] == b"\xFF" * 2 or oob_block[8:0xA] == b"\xFF" * 2:
            continue

        block_id = int.from_bytes(oob_block[0x8:0xA], "little")
        
        if block_id in matched:
            print(f"WARN: duplicate block id (Block id: {hex(block_id)}, OOB offset: {hex(block * oob_block_size)})")
        else:
            chunk_dicts.append({"fat": data_block, "block_id": block_id})
        matched.add(block_id)
    
    sorted_chunk_dicts = sorted(chunk_dicts, key=lambda x:x["block_id"])
    fat = bytearray((sorted_chunk_dicts[-1]["block_id"]+1) * data_block_size)
    for chunk_dict in sorted_chunk_dicts:
        #print(hex(chunk_dict["block_id"]))
        fat[chunk_dict["block_id"] * data_block_size : 
            (chunk_dict["block_id"]+1) * data_block_size] = chunk_dict["fat"]
            
    with open(output, "wb") as outf:
        outf.write(fat)

if __name__ == "__main__":
    main()