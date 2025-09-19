import argparse
import os

LAYOUT = [512, 16]

parser = argparse.ArgumentParser(description="Raw chip-off dump to JTAG dump converter for KDDI Qualcomm phones.")
parser.add_argument("input")
parser.add_argument("input_type", choices=["interleaved", "separated"], help="How input file(s) (DATA and OOB) are stored.",)
parser.add_argument("-o", "--output", default=None)

args = parser.parse_args()

output = args.output or os.path.splitext(args.input)[0] + "_jtagged.bin"

print("Start")

dump_size = os.path.getsize(args.input)
(data_page_size, oob_page_size) = LAYOUT
page_size = data_page_size + oob_page_size
oob_buffer = bytearray()

if args.input_type == "interleaved":
    with open(args.input, "rb") as dump, open(output, "wb") as outf:
        for i in range(dump_size // page_size):
            data_chunk = dump.read(page_size)
            if not data_chunk: break

            new_chunk = bytearray()
            new_chunk += data_chunk[:0x1D0]
            new_chunk += data_chunk[0x1D2:0x20E]
            new_chunk += data_chunk[0x20E:0x210]
            new_chunk += data_chunk[0x20E:0x210]

            outf.write(new_chunk[:data_page_size])
            oob_buffer += new_chunk[data_page_size:]
        outf.write(oob_buffer)

elif args.input_type == "separated":
    with open(args.input, "rb") as dump, open(os.path.splitext(args.input)[0] + ".oob", "rb") as oob, open(output, "wb") as outf:
        for i in range(dump_size // data_page_size):
            data_chunk = dump.read(data_page_size)
            oob_chunk = oob.read(oob_page_size)
            if not data_chunk: break
            if not oob_chunk: break

            new_data_chunk = bytearray()
            new_data_chunk += data_chunk[:0x1D0]
            new_data_chunk += data_chunk[0x1D2:0x200]
            new_data_chunk += oob_chunk[:0x2]

            new_oob_chunk = bytearray()
            new_oob_chunk += oob_chunk[0x2:0xE]
            new_oob_chunk += oob_chunk[0xE:0x10]
            new_oob_chunk += oob_chunk[0xE:0x10]

            outf.write(new_data_chunk)
            oob_buffer += new_oob_chunk
        outf.write(oob_buffer)
else:
    raise Exception("")

print("Completed.")
