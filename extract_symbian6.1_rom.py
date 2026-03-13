import argparse
import struct
from enum import Enum
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class NodeType(Enum):
    FILE = "file"
    DIRECTORY = "directory"

class FileSystemBase:
    def __init__(self, data):
        self.data = data
        self.data_size = len(self.data)

    def read_u16(self, offset):
        return struct.unpack_from("<H", self.data, offset)[0]

    def read_u32(self, offset):
        return struct.unpack_from("<I", self.data, offset)[0]

class SymbianROMExtractor(FileSystemBase):
    def __init__(self, input_path, output_dir):
        self.input_path = Path(input_path)
        self.output_root_dir = Path(output_dir)
        self.data = None
        self._load_data()
        self._parse_header()
        super().__init__(self.data) 

    def _load_data(self):
        with open(self.input_path, "rb") as f:
            self.data = f.read()

    def _parse_header(self):
        fields = [
            ("iJump", "124s"),
            ("iRestartVector", "I"),   
            ("iTime", "q"),          
            ("iTimeHi", "I"),
            ("iRomBase", "I"),
            ("iRomSize", "I"),
            ("iRomRootDirectoryList", "I"),
            ("iKernDataAddress", "I"),
            ("iKernelLimit", "I"),
            ("iPrimaryFile", "I"),
            ("iSecondaryFile", "I"),
            ("iCheckSum", "I"),
            ("iHardware", "I"),
            ("iLanguage", "q"),      
            ("iKernelConfigFlags", "I"),
            ("iRomExceptionSearchTable", "I"),
            ("iRomHeaderSize_raw", "I"),
            ("iRomSectionHeader", "I"),
            ("iTotalSvDataSize", "i"), 
            ("iVariantFile", "I"),
            ("iExtensionFile", "I"),
            ("iRelocInfo", "I"),
            ("iOldTraceMask", "I"),
            ("iUserDataAddress", "I"),
            ("iTotalUserDataSize", "i"),
            ("iDebugPort", "I"),
            ("iVersion_major", "i"),
            ("iVersion_minor", "i"),
            ("iVersion_build", "i"),
            ("iCompressionType", "I"),
            ("iCompressedSize", "I"),
            ("iUncompressedSize", "I"),
            ("iDisabledCapabilities_0", "I"),
            ("iDisabledCapabilities_1", "I"),
            ("iTraceMask_0", "I"),
            ("iTraceMask_1", "I"),
            ("iTraceMask_2", "I"),
            ("iTraceMask_3", "I"),
            ("iTraceMask_4", "I"),
            ("iTraceMask_5", "I"),
            ("iTraceMask_6", "I"),
            ("iTraceMask_7", "I"),
        ]
      
        fmt = "<" + "".join(f for (_, f) in fields)
        self.header_info = dict(
            zip(
              [field[0] for field in fields],
              struct.unpack_from(fmt, self.data)
            )
        )
    
    def virt_to_phys(self, virtual_address):
        physical_address = virtual_address - self.header_info["iRomBase"]
        if physical_address < 0 or physical_address > self.data_size:
            raise ValueError(f"Invalid virtual address {hex(virtual_address)} or base address {hex(self.header_info["iRomBase"])} ({hex(physical_address)})")
        return physical_address
    
    def read_TRomRootDirectoryList(self, off):
        trom_dir_offs = []
        inum_dirs = self.read_u32(off)
        for i in range(inum_dirs):
            trom_dir_offs.append(
                self.virt_to_phys(
                    self.read_u32(off + 8 + i * 4)
                )
            )
        return trom_dir_offs
        
    class TRomDir(FileSystemBase):
        def __init__(self, symbian_rom_extractor, trom_dir_off, base_dir):
            super().__init__(symbian_rom_extractor.data) 
            self.trom_dir_off = trom_dir_off 
            self.symbian_rom_extractor = symbian_rom_extractor
            self.base_dir = base_dir
            self.read(trom_dir_off)
            
        def read(self, trom_dir_off):
            self.total_trom_entry_size = self.read_u32(trom_dir_off)
            assert self.total_trom_entry_size > 0
            entry_start = trom_dir_off + 4
            count = 0

            off = entry_start
            end_off = trom_dir_off + self.total_trom_entry_size
            logger.info(f"Started reading, start: {hex(trom_dir_off)}, end_off: {hex(end_off)}")
            while True:
                logger.debug(f"Started parsing entries {hex(off)}")
                trom_entry = SymbianROMExtractor.TRomEntry(self.symbian_rom_extractor, off, self.base_dir)
                logger.debug(f"- name: {trom_entry.name}, size:{trom_entry.filesize}, offset:{hex(trom_entry.offset)}, flag:{trom_entry.flag}, type: {trom_entry.node_type}")
                
                if trom_entry.node_type == NodeType.DIRECTORY:
                    new_dir = self.base_dir / trom_entry.name
                    os.makedirs(new_dir, exist_ok=True)
                    SymbianROMExtractor.TRomDir(self.symbian_rom_extractor, trom_entry.offset, new_dir)
                else:
                    trom_entry.extract()

                off += trom_entry.entry_size
                count += 1
                if off >= end_off:
                    break
    
    class TRomEntry(FileSystemBase):
        def __init__(self, symbian_rom_extractor, trom_entry_off, base_dir):
            super().__init__(symbian_rom_extractor.data) 
            self.entry_size = None
            self.name = None
            self.node_type = None
            self.symbian_rom_extractor = symbian_rom_extractor
            self.base_dir = base_dir
            self.read(trom_entry_off)

        def read(self, trom_entry_off):
            format = "<IIBB"
            struct_size = struct.calcsize(format)
            self.filesize, self.offset, self.flag, self.name_len = struct.unpack_from(
                format, self.data, trom_entry_off
            )

            self.node_type = NodeType.DIRECTORY if self.flag == 16 else NodeType.FILE
            name_size = self.name_len * 2

            self.name = self.data[
                trom_entry_off + struct_size : 
                trom_entry_off + struct_size + name_size
            ].decode("utf-16le")

            self.offset = self.symbian_rom_extractor.virt_to_phys(self.offset)

            self.entry_size = struct_size + name_size
            # padding for alignment
            rem = self.entry_size % 4
            if rem != 0:
                self.entry_size += (4 - rem)

        def extract(self):
            file_data = self.data[self.offset : self.offset + self.filesize]
            with open(self.base_dir / self.name, "wb") as outf:
                outf.write(file_data)
            

    def extract(self):
        RomRootDirectoryList_off = self.virt_to_phys(self.header_info["iRomRootDirectoryList"])
        TRomDir_offs = self.read_TRomRootDirectoryList(RomRootDirectoryList_off)
        logger.debug(f"RomRootDirectoryList_off: {hex(RomRootDirectoryList_off)}")
        logger.debug(f"TRomDir_offs: {', '.join([hex(off) for off in TRomDir_offs])}")
        for TRomDir_off in TRomDir_offs:
            SymbianROMExtractor.TRomDir(self, TRomDir_off, self.output_root_dir)
            
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Symbian 6.1 ROM Extractor")
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    logging.basicConfig(level=logging.DEBUG)
    symbian_rom = SymbianROMExtractor(args.input, args.output)
    symbian_rom.extract()