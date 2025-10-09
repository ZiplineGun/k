import os
import argparse

layouts = [[512, 16], [1024, 32], [2048, 64], [4096, 128], [8192, 256]]

def main(mixdump_path, layout=None, out_nand=None, out_oob=None):
    filename = os.path.splitext(os.path.basename(mixdump_path))[0]
    mixdump_size = os.path.getsize(mixdump_path)

    print(f"Input: {mixdump_path}")

    if layout is None:
        for i, (data_size, oob_size) in enumerate(layouts):
            print(f"{i}: Data = {data_size} Bytes, OOB = {oob_size} bytes, divisible = {mixdump_size % (data_size+oob_size) == 0}")
        inpn = int(input('Enter the layout number: '))
        layout = layouts[inpn]

    data_size, oob_size = layout

    out_nand = out_nand or os.path.join(os.path.dirname(mixdump_path), f"{filename}_separated_{data_size}.bin")
    out_oob = out_oob or os.path.join(os.path.dirname(mixdump_path), f"{filename}_separated_{data_size}.oob")

    separate_nand_oob(mixdump_path, data_size, oob_size, out_nand, out_oob)

    print(f"Done")

def separate_nand_oob(mixdump_path, data_size, oob_size, out_nand=None, out_oob=None):

    print(f"Started separating {data_size}/{oob_size}")
    
    with open(mixdump_path, "rb") as in_nandf, open(out_nand, "wb") as out_nandf, open(out_oob, "wb") as out_oobf:
        while True:
            nand_temp = in_nandf.read(data_size)
            if not nand_temp: break

            oob_temp = in_nandf.read(oob_size)
            if not oob_temp: break

            out_nandf.write(nand_temp)
            out_oobf.write(oob_temp)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("")
    parser.add_argument("input")
    parser.add_argument("-l", "--layout", type=int, default=None, choices=range(len(layouts)), help=" ".join([f"{i}: {l}," for i, l in enumerate(layouts)]))
    parser.add_argument("-od", "--output_nand", default=None)
    parser.add_argument("-oo", "--output_oob", default=None)
    args = parser.parse_args()

    main(args.input, layouts[args.layout], args.output_nand, args.output_oob)
