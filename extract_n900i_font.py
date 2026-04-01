import os 
import struct
from PIL import Image
import argparse

perser = argparse.ArgumentParser("N900i FONT extracter")
perser.add_argument("input", help="N900i NOR file")
perser.add_argument("output_dir")
args = perser.parse_args()


output_strs = [
    '16x12_basic', '16x12_kanji', '16x12_emoji','16x12_other_font', '16x12_unknown1',
    '16x12_unknown2', '16x12_unknown3', '16x12_unknown4', '16x12_unknown5',
    '16x16_basic', '16x16_kanji', '16x16_emoji', '16x16_other_font', '16x16_unknown1',
    '16x16_unknown2', '16x16_unknown3', '16x16_unknown4', '16x16_unknown5',
    '24x20_basic', '24x20_kanji', '24x20_emoji', '24x20_other_font', '24x20_unknown1',
    '24x20_unknown2', '24x20_unknown3', '24x20_unknown4', '24x20_unknown5',
    '24x24_basic', '24x24_kanji', '24x24_emoji', '24x24_other_font','24x24_unknown1',
    '24x24_unknown2', '24x24_unknown3', '24x24_unknown4', '24x24_unknown5', '24x24_unknown6','24x24_unknown7',
    '32x30_basic', '32x30_kanji', '32x30_emoji', '32x30_other_font', '32x30_unknown1',
    '32x30_unknown2', '32x30_unknown3', '32x30_unknown4', '32x30_unknown5', '32x30_unknown6', '32x30_unknown7', 
    '32x30_unknown8', 
]

os.makedirs(args.output_dir, exist_ok=True)

with open(args.input, "rb") as inf:
    nor_data = inf.read()


table = nor_data[0x6ECEE0 : 0x6ECFAC]

start = None
for i, entry_off in enumerate(range(0, len(table), 4)):
    end = int.from_bytes(table[entry_off : entry_off + 4], "little")
    if start is not None:
        with open(os.path.join(args.output_dir, f"{i}_{hex(start)}_{output_strs[i-1]}.bin"), "wb") as outf:
            outf.write(nor_data[start : end])
    start = end

