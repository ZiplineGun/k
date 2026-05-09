# TODO:
# - Support for compressed formats other than Type 0 (Skipped section)
# - Unraveling the reasons why the resolution differs from the metadata.
# - For the reasons mentioned above, not all images are currently being extracted.


import os
import math
import sys
from PIL import Image
import argparse

parser = argparse.ArgumentParser(description="")
parser.add_argument("input", help="V601SH LRS1B28-s.bin")
parser.add_argument("output_dir")
args = parser.parse_args()

START_OFFSET = 0x20F5A 
METADATA_SIZE = 0x26


def read_le16(data, offset):
    return data[offset] | (data[offset + 1] << 8)


def raw4bpp_to_image(
    raw_bytes: bytes,
    palette_bytes: bytes,
    width: int,
    height: int,
) -> Image.Image:
    palette = []

    # Convert RGB565 palette entries to RGBA8888 tuples
    for i in range(0, 32, 2):
        v = palette_bytes[i] | (palette_bytes[i + 1] << 8)

        r5 = (v >> 11) & 0x1F
        g6 = (v >> 5) & 0x3F
        b5 = v & 0x1F

        palette.append((
            r5 * 255 // 31,
            g6 * 255 // 63,
            b5 * 255 // 31,
            255,
        ))

    # Add alpha channel
    for i, (r, g, b, a) in enumerate(palette):
        if r == 255 and g == 255 and b == 255:
            palette[i] = (r, g, b, 0)

    # Instead, the bluish white is replaced with white.
    for i, (r, g, b, a) in enumerate(palette):
        if r == (0b11011 * 255 // 31) and g == 255 and b == 255:
            palette[i] = (255, 255, 255, a)

    # Convert 4BPP
    pixels = []

    for b in raw_bytes:
        lo = b & 0x0F
        hi = (b >> 4) & 0x0F
        pixels.append(lo)
        pixels.append(hi)

    # Create
    img = Image.new("RGBA", (width, height))
    px = img.load()

    total = width * height

    for i in range(total):
        idx = pixels[i] if i < len(pixels) else 0
        px[i % width, i // width] = palette[idx & 0x0F]

    return img


def main():
    os.makedirs(args.output_dir, exist_ok=True)

    with open(args.input, "rb") as f:
        f.seek(0xD12000)
        data = f.read()

    offset = START_OFFSET
    file_size = len(data)
    index = 0

    while offset + METADATA_SIZE <= file_size:
        meta_start = offset
        meta_end = offset + METADATA_SIZE

        metadata = data[meta_start:meta_end]
        
        type_ = read_le16(metadata, 0)
        width = read_le16(metadata, 2)
        height = read_le16(metadata, 4)
        
        # ???
        if width == 19 and height == 19:
            if offset < 0x2DC46:
                width = 20
                height = 19
            elif offset < 0x2DF66:
                width = 38
                height = 19
            else:
                width = 20
                height = 19
            
        if width == 13 and height == 13:
            width = 14
            height = 13
            
        if width == 11 and height == 13:
            width = 12
            height = 13
            
        if width == 11 and height == 19:
            width = 12
            height = 19
            
        if width == 19 and height == 20:
            width = 40
            height = 20
            
        if width == 19 and height == 38:
            width = 20
            height = 38
            
        # 4BPP → 0.5 byte per pixel
        image_size = math.ceil(width * height / 2)

        img_start = meta_end
        img_end = img_start + image_size

        if img_end > file_size:
            print(f"EOF reached at offset 0x{offset:X}")
            break

        image_data = data[img_start:img_end]

        base_name = f"{index:04d}_0x{meta_start:X}_type{type_}_{width}x{height}"

        meta_path = os.path.join(args.output_dir, base_name + ".meta.bin")
        img_path = os.path.join(args.output_dir, base_name + ".raw.bin")
        png_path = os.path.join(args.output_dir, base_name + ".png")

        with open(meta_path, "wb") as mf:
            mf.write(metadata)

        with open(img_path, "wb") as imf:
            imf.write(image_data)
            
        raw4bpp_to_image(image_data, metadata[6:], width, height).save(png_path)

        print(f"Saved: {base_name} (type={type_}, w={width}, h={height}, size={image_size} raw={metadata.hex(" ")})")
        #assert type_ == 0, hex(offset)
        
        offset = img_end
        
        # Align
        if offset % 2 != 0:
            offset += 1
        
        # skip type2/5 (Unknown compression method)
        if offset == 0x25870:
            offset = 0x26DB4
        if offset == 0x280B0:
            offset = 0x293F2
        if offset == 0x36A38:
            offset = 0x374B8
        if offset == 0x381E8:
            offset = 0x39124
        if offset == 0x393D0:
            offset = 0x44F12
        if offset == 0x4E392:
            offset = 0x4ED38
            
        index += 1


if __name__ == "__main__":
    main()