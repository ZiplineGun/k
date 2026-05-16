import os
import struct
import argparse
from PIL import Image

parser = argparse.ArgumentParser(description="")
parser.add_argument("input", help="V601N-3_PF38F3352LLZDQ0-f2.bin")
parser.add_argument("-r", "--raw_output", action="store_true")
parser.add_argument("out_dir")
args = parser.parse_args()

# Codepoint: https://web.archive.org/web/20060703170125/http://developers.vodafone.jp/dp/tool_dl/web/picword_top.php
# Page [2, 3] [1] [4] [5, 6]

EMOJI_INFOS = [
    {
        "table_start": 0xDA1EA0,
        "code_points": [*range(0xE101, 0xE15B), *range(0xE201, 0xE25B)],
        "width": 12,
        "height": 12,
        "is_short": False,
    },
    {
        "table_start": 0xE2C040,
        "code_points": [*range(0xE001, 0xE05B)],
        "width": 12,
        "height": 12,
        "is_short": True,
    },
    {
        "table_start": 0xDB0DF8,
        "code_points": [*range(0xE301, 0xE34E)],
        "width": 12,
        "height": 12,
        "is_short": False,
    },
    {
        "table_start": 0xDB57D0,
        "code_points": [*range(0xE401, 0xE44D), *range(0xE501, 0xE540)],
        "width": 12,
        "height": 12,
        "is_short": False,
    },
    {
        "table_start": 0xE46248,
        "code_points": [*range(0xE101, 0xE15B), *range(0xE201, 0xE25B)],
        "width": 16,
        "height": 16,
        "is_short": False,
    },
    {
        "table_start": 0xE406E0,
        "code_points": [*range(0xE001, 0xE05B)],
        "width": 16,
        "height": 16,
        "is_short": True,
    },
    {
        "table_start": 0xE46248,
        "code_points": [*range(0xE301, 0xE34E)],
        "width": 16,
        "height": 16,
        "is_short": False,
    },
    {
        "table_start": 0xE4E5B0,
        "code_points": [*range(0xE401, 0xE44D), *range(0xE501, 0xE540)],
        "width": 16,
        "height": 16,
        "is_short": False,
    },
    {
        "table_start": 0xF287E8,
        "code_points": [*range(0xE101, 0xE15B), *range(0xE201, 0xE25B)],
        "width": 20,
        "height": 20,
        "is_short": False,
    },
    {
        "table_start": 0xF48318,
        "code_points": [*range(0xE001, 0xE05B)],
        "width": 20,
        "height": 20,
        "is_short": True,
    },
    {
        "table_start": 0xF51120,
        "code_points": [*range(0xE301, 0xE34E)],
        "width": 20,
        "height": 20,
        "is_short": False,
    },
    {
        "table_start": 0xF5DD18,
        "code_points": [*range(0xE401, 0xE44D), *range(0xE501, 0xE540)],
        "width": 20,
        "height": 20,
        "is_short": False,
    },
]

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

RGB332_PALETTE = generate_rgb332_palette()
ALPHA_COLOR = (0xff, 0xff, 0xaa)

with open(args.input, "rb") as inf:
    nor_data =  inf.read()

for emoji_info in EMOJI_INFOS:
    frames = []
    off = emoji_info["table_start"]
    out_dir = os.path.join(args.out_dir, f"{emoji_info['width']}x{emoji_info['height']}")
    os.makedirs(out_dir, exist_ok=True)
    
    if emoji_info["is_short"]:
        entry_size = 4
        while True:
            unk1, unk2 = struct.unpack("<HH", nor_data[off : off + entry_size])
            if unk1 != 2 or unk2 !=0xFE:
                break
            frames.append(1)
            off += entry_size
    else:
        entry_size = 8
        while True:
            unk1, unk2, count, frame = struct.unpack("<HHHH", nor_data[off : off + entry_size])
            if unk1 != 2 or unk2 !=0xFE:
                break
            frames.append(frame)
            off += entry_size
    
    code_points = emoji_info["code_points"].copy()
    chara_num = len(frames)
    for _ in range(chara_num):
        if len(code_points) > 0:
            code_point = code_points.pop(0)
        else:
            code_point = 0xFFFF
        
        for frame in range(frames.pop(0)):
            raw_image_size = emoji_info["width"] * emoji_info["height"]
            raw_image = nor_data[off : off + raw_image_size]
            
            img = Image.frombytes("P", (emoji_info["width"], emoji_info["height"]), raw_image) 
            img.putpalette(RGB332_PALETTE)
            img = img.convert("RGBA")
            pixels = img.load() 
            for y in range(emoji_info["height"]):
                for x in range(emoji_info["width"]):
                    r, g, b, a = pixels[x, y]
                    if (r, g, b) == ALPHA_COLOR:
                        pixels[x, y] = (r, g, b, 0) 
            
            out_path = os.path.join(out_dir, f"{code_point:04X}_{frame:02}")
                
            if args.raw_output:
                out_path += ".bin"
                with open(out_path, "wb") as outf:
                    outf.write(raw_image)
            else:
                out_path += ".png"
                img.save(out_path)
            
            off += raw_image_size
