# -*- coding: utf-8 -*-

import sys
import io

def string_to_number(s):
    """
    Converts a string representing a number into an integer.
    Supports both decimal and hexadecimal (0x-prefixed) formats.

    Parameters:
        s (str): The input string to convert.

    Returns:
        int: The converted number.

    Raises:
        ValueError: If the string cannot be converted to a number.
    """
    try:
        if s.startswith(('0x', '0X')):
            # Convert hexadecimal string to integer
            return int(s, 16)
        else:
            # Convert decimal string to integer
            return int(s)
    except ValueError as e:
        raise ValueError(f"Invalid number string: {s}") from e

EVERY = string_to_number(sys.argv[1])
if EVERY % 0x10 != 0: raise ValueError("Must be a multiple of 0x10.")

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main(binary):
    print("Offset(h)  00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F   Decode")
    binary_size = len(binary)
    
    for offset in range(0, binary_size, EVERY):
        start = offset
        end = min(start+0x10, binary_size)
        
        offset_str = f"{start:0=9X}"
        hex_str = " ".join(f"{byte:0=2X}" for byte in binary[start:end])
        decode_str = encode_bytes(binary[start:end])
        
        print(f"""{offset_str}  {hex_str}  |{decode_str}|""")

def encode_bytes(data):
    return "".join(chr(b) if chr(b).isprintable() else "." for b in data)

if __name__ == "__main__":
    with open(sys.argv[2], "rb") as file:
        main(file.read())