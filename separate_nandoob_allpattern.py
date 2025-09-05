import sys
import os

layouts = [[512, 16], [1024, 32], [2048, 64], [4096, 128], [8192, 256]]

def main():
    nand_path = sys.argv[1]
    print(f"Input: {nand_path}")
        
    for layout in layouts:
        nand_pagesize = layout[0]
        oob_pagesize = layout[1]
        
        nandname = os.path.splitext(os.path.basename(nand_path))[0]
        out_nand = os.path.join(os.path.dirname(nand_path), f"separated_{nandname}_{str(nand_pagesize)}.bin")
        out_oob = os.path.join(os.path.dirname(nand_path), f"separated_{nandname}_{str(nand_pagesize)}.oob")
        print(f"\nStarted separate {nand_pagesize}/{oob_pagesize}")
        
        with open(nand_path, "rb") as in_nandf:
            in_size = os.path.getsize(nand_path)
            if in_size % (nand_pagesize+oob_pagesize) != 0:
                print("The nand/oob size is not appropriate.")
                continue
            
            with open(out_nand, "wb") as out_nandf:
                with open(out_oob, "wb") as out_oobf:
                    while True:
                        nand_temp = in_nandf.read(nand_pagesize)
                        if not nand_temp: break
                        oob_temp = in_nandf.read(oob_pagesize)
                        if not oob_temp: break
                        out_nandf.write(nand_temp)
                        out_oobf.write(oob_temp)
                    print(f"Succeed => {out_nand},\n{out_oob}")


if __name__ == "__main__":
    main()
