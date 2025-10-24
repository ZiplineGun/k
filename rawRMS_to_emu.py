import os
import argparse
import struct

parser = argparse.ArgumentParser(description="Raw RMS converter")
parser.add_argument("input")
parser.add_argument("out_dir")
parser.add_argument("-of", "--offset", default=None,
                    help="Hex notation (0x***) can be used. If not specified, auto-detect.",
                    type=lambda x: int(x, 0)
)
args = parser.parse_args()

with open(args.input, "rb") as inf:
    rms_data = inf.read()

os.makedirs(args.out_dir, exist_ok=True)

def get_rms_partitions(rms_data):
    print(args.offset)
    off = args.offset or 1 # Skip offset 0
    off -= 1
    while (off := rms_data.find(b"\x00\x00\x00\x01", off+1)) != -1:
        print("Trying", hex(off))
        rms_partitions = []
        inner_off = off
        i = 1

        try:
            while True:
                if (inner_off+1) == len(rms_data) or rms_data[inner_off:] == b"\xFF" * (len(rms_data) - inner_off):
                     return rms_partitions
                
                partition = int.from_bytes(rms_data[inner_off : inner_off + 4], "big")
                print("partition", partition,  "offset", hex(inner_off))

                if partition != i:
                    break

                size = int.from_bytes(rms_data[inner_off + 4 : inner_off + 8], "big")
                content = rms_data[inner_off + 8 : inner_off + 8 + size]
                rms_partitions.append(content)
                i += 1
                inner_off += 8 + size
        except IndexError:
                break
        
        if args.offset is not None:
            break
            
    return rms_partitions


rms_partitions = get_rms_partitions(rms_data)
if len(rms_partitions) == 0:
     raise Exception("Failed to detect RMS.")

total_size = 0
with open(os.path.join(args.out_dir, "mexa_01"), "wb") as out01f, open(os.path.join(args.out_dir, "mexa_02"), "wb") as out02f:
    for i, rms_partition in enumerate(rms_partitions):
        out02f.write(rms_partition)

        size = len(rms_partition)
        out01f.write(struct.pack(">IIII", 0, i+1, total_size, size))
        total_size += size

        with open(os.path.join(args.out_dir, f"{i+1}.rms"), "wb") as outrf:
            outrf.write(rms_partition)
