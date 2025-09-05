# -*- coding: utf-8 -*-

import os
import sys
import re
import extract_rsrc1

START_OFFSET = 0x60
DIR_LENGTH = 0x44
FILE_LENGTH = 0x48

if __name__ == "__main__":
    for file_path in sys.argv[1:]:
        print("Start")
        with open(file_path, "rb") as file:
            rc1_content = file.read()
        extract_rsrc1.main(rc1_content, START_OFFSET, DIR_LENGTH, FILE_LENGTH)
        print("End")
