import os 
import struct
from PIL import Image
import argparse
from typing import Union

do_convert = True

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


def convert_rgb565_bytes_to_image(
    data: Union[bytes, bytearray],
    width: int,
    height: int,
    byteorder: str = 'little',       # 'little' or 'big'
    stride_bytes: int | None = None, # bytes per row (including padding). If None, uses width*2
    offset: int = 0,                 # offset in `data` where image data starts (bytes)
    top_down: bool = True            # True: the start of `data` is the top row, False: start is the bottom row
) -> Image.Image:
    """
    data: RGB565 raw bytes (consecutive pixels, 2 bytes per pixel)
    width,height: image size (pixels)
    byteorder: 'little' (little-endian) or 'big' (big-endian)
    stride_bytes: number of bytes per row (specify when there is padding)
    offset: start position of the image within `data` (bytes)
    top_down: True -> the first row in `data` is the top row (normal layout)
    Returns: PIL.Image.Image (mode='RGB')
    """
    if byteorder not in ('little', 'big'):
        raise ValueError("byteorder must be 'little' or 'big'")

    width = int(width)
    height = int(height)
    stride = int(stride_bytes) if stride_bytes is not None else width * 2
    offset = int(offset)
    mv = memoryview(data)

    # Check minimum required bytes (start of last row + width*2)
    min_needed = offset + (height - 1) * stride + width * 2
    if len(mv) < min_needed:
        raise ValueError(
            f"Insufficient data length: {len(mv)} bytes "
            f"(minimum required: {min_needed} bytes)"
        )

    img = Image.new('RGB', (width, height))

    # Process and paste each row
    for row_idx in range(height):
        file_row = row_idx if top_down else (height - 1 - row_idx)
        read_pos = offset + file_row * stride
        row_slice = mv[read_pos: read_pos + width * 2]

        if len(row_slice) < width * 2:
            raise ValueError(f"Row data is incomplete: row {row_idx}")

        row_out = bytearray()  # RGB byte sequence for one row (width * 3)

        if byteorder == 'little':
            # little-endian: low byte first, then high byte
            for i in range(0, width * 2, 2):
                low = row_slice[i]
                high = row_slice[i + 1]
                val = low | (high << 8)

                r5 = (val >> 11) & 0x1F
                g6 = (val >> 5) & 0x3F
                b5 = val & 0x1F

                r8 = (r5 << 3) | (r5 >> 2)
                g8 = (g6 << 2) | (g6 >> 4)
                b8 = (b5 << 3) | (b5 >> 2)

                row_out.extend((r8, g8, b8))
        else:
            # big-endian: high byte first, then low byte
            for i in range(0, width * 2, 2):
                high = row_slice[i]
                low = row_slice[i + 1]
                val = (high << 8) | low

                r5 = (val >> 11) & 0x1F
                g6 = (val >> 5) & 0x3F
                b5 = val & 0x1F

                r8 = (r5 << 3) | (r5 >> 2)
                g8 = (g6 << 2) | (g6 >> 4)
                b8 = (b5 << 3) | (b5 >> 2)

                row_out.extend((r8, g8, b8))

        # Paste the single row into the image
        row_img = Image.frombytes('RGB', (width, 1), bytes(row_out))
        y = row_idx if top_down else (height - 1 - row_idx)
        img.paste(row_img, (0, y))

    return img


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
        
        if do_convert and ext == "bin":
            try:
                if type == 5:
                    img = convert_rgb565_bytes_to_image(out_data, width, height)
                else:
                    img = Image.frombytes("P", (width, height), out_data) 
                    img.putpalette(generate_rgb332_palette())

                # Transparent background color
                img = img.convert("RGBA")
                alpha_color = (0, 36, 0)
                pixels = img.load() 
                for y in range(height):
                    for x in range(width):
                        r, g, b, a = pixels[x, y]
                        if (r, g, b) == alpha_color:
                            pixels[x, y] = (r, g, b, 0) 

                img.save(os.path.join(args.output_dir, f"{out_basename}_converted.png"))
            except Exception as e:
                print(f"Error: {out_basename}.{ext}", e)
                with open(os.path.join(args.output_dir, f"{out_basename}.{ext}"), "wb") as outf:
                    outf.write(out_data)
        else:
            with open(os.path.join(args.output_dir, f"{out_basename}.{ext}"), "wb") as outf:
                outf.write(out_data)

