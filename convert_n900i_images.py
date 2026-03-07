import os 
import struct
from PIL import Image
import argparse
from typing import Union

DO_CONVERT = True
ALPHA_COLOR = (0, 36, 0)

perser = argparse.ArgumentParser("N900i image converter")
perser.add_argument("input", help="N900i NOR file")
perser.add_argument("output_dir")
args = perser.parse_args()

os.makedirs(args.output_dir, exist_ok=True)

with open(args.input, "rb") as inf:
    nor_data = inf.read()

table_offs = [[0xF31380, 0xF350FC], [0x1924FF4, 0x192D0A0]]

def generate_rgb332_palette():
    palette = []
    for i in range(256):
        r3 = (i >> 5) & 0x07
        g3 = (i >> 2) & 0x07
        b2 = i & 0x03
        r8 = (r3 << 5) | (r3 << 2) | (r3 >> 1)
        g8 = (g3 << 5) | (g3 << 2) | (g3 >> 1)
        b8 = (b2 << 6) | (b2 << 4) | (b2 << 2) | b2
        palette.extend((r8, g8, b8))
    return bytearray(palette)


for start, end in table_offs:
    table = nor_data[start : end]

    for entry in range(0, len(table), 20):
        off, size, type, width, height = struct.unpack("<5I", table[entry : entry + 20])

        ext = "bin"
        if type == 2: 
            ext = "gif"
        elif type == 3:
            ext = "jpeg"
        elif type == 6:
            ext = "swf"
        elif type == 7: 
            ext = "afd" # broken

        out_data = nor_data[off : off + size]
        out_basename = f"type{type}_{width}x{height}_{hex(off)}"
        
        if DO_CONVERT and ext == "bin":
            try:
                if type == 5:
                    img = Image.frombytes("RGB", (width, height), out_data, "raw","BGR;16")
                else:
                    img = Image.frombytes("P", (width, height), out_data) 
                    img.putpalette(generate_rgb332_palette())

                # Transparent background color
                img = img.convert("RGBA")
                pixels = img.load() 
                for y in range(height):
                    for x in range(width):
                        r, g, b, a = pixels[x, y]
                        if (r, g, b) == ALPHA_COLOR:
                            pixels[x, y] = (r, g, b, 0) 

                img.save(os.path.join(args.output_dir, f"{out_basename}_converted.png"))
            except Exception as e:
                print(f"Error: {out_basename}.{ext}", e)
                with open(os.path.join(args.output_dir, f"{out_basename}.{ext}"), "wb") as outf:
                    outf.write(out_data)
        else:
            with open(os.path.join(args.output_dir, f"{out_basename}.{ext}"), "wb") as outf:
                outf.write(out_data)

