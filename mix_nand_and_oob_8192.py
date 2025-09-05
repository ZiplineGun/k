import sys
import os

NAND_BYTE_STEP = 8192
OOB_BYTE_STEP = 256

def main():
    nand = sys.argv[1]
    nandname = os.path.splitext(os.path.basename(nand))[0]
    oob = os.path.join(os.path.dirname(nand), f"{nandname}.oob")
    print(f"nand: {nand}\noob: {oob}")
    output_path = os.path.join(os.path.dirname(nand), f"{nandname}_mixed.bin")
    
    with open(nand, "rb") as file:
        nand_content = file.read()
        
    with open(oob, "rb") as file:
        oob_content = file.read()
        
    with open(output_path, "wb") as file:
        mixed_content = bytearray()
        nand_offset = 0
        oob_offset = 0
        
        while True:
            if nand_offset+NAND_BYTE_STEP > len(nand_content): break
            if oob_offset+OOB_BYTE_STEP > len(oob_content): break
            
            file.write(nand_content[nand_offset:nand_offset+NAND_BYTE_STEP])
            file.write(oob_content[oob_offset:oob_offset+OOB_BYTE_STEP])
            
            nand_offset += NAND_BYTE_STEP
            oob_offset += OOB_BYTE_STEP
        


if __name__ == "__main__":
    main()