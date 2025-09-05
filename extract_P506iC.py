import os
import sys

res = bytearray()
with open(sys.argv[1], "rb") as file:
    size = os.path.getsize(sys.argv[1])
    

    res += file.read(0x800)
    file.read(0x6)
    res += file.read(0x800)
    file.read(0x6)
    res += file.read(0x800)
    file.read(0x6)
    res += file.read(0x800)
    file.read(0x6)
    res += file.read()
    
    
    fat_offs = []
    off = -1
    while True:
        if (off := res.find(b"MEIPIEFS", off+1)) == -1:
            break
        if (off-3) % 0x10 != 0: print("WARNING: ")
        if res[off-3+0x36:off-3+0x36+3] == b"FAT":
            fat_offs.append(off-3)
    fat_offs.append(len(res))


    for i in range(len(fat_offs) - 1):
        print(outpath := os.path.join(os.path.dirname(sys.argv[1]), f"FAT_0x{fat_offs[i]:07X}.bin"))
        with open(outpath, "wb") as file:
            file.write(res[fat_offs[i] : fat_offs[i+1]])
