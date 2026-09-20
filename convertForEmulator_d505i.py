import re
import sys
import os
import datetime
import struct
import shutil
import fnmatch
import email.utils
import traceback
from pathlib import Path
from enum import Enum, auto
import argparse

class SpType(Enum):
    SINGLE = auto()
    MULTI = auto()

CONFIGS = {
    "D505i": {
        "sp_type": SpType.MULTI,
        "draw_area": "240x270",
        "package_url_off": 0x448,
        "app_name_off": 0x548,
        "app_ver_off": 0x55D,
        "kvm_ver_off": 0x568,
        "profile_ver_off": 0x573,
        "app_class_off": 0x57E,
        "app_param_off": 0x67E,
        "target_device_off": 0x77E,
        "last_modified_off": 0xA34,
        "app_size_off": 0xA3C,
        "sp_size_off": 0xA40,
    },

}

def parse_datetime(data: bytes) -> str:
    if len(data) != 8:
        raise ValueError("data must be exactly 8 bytes")

    year = int.from_bytes(data[0:2], "big")
    month = data[2]
    day = data[3]
    weekday = data[4]
    hour = data[5]
    minute = data[6]
    second = data[7]

    weekdays = ["", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    months = [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    if not 1 <= weekday <= 7:
        raise ValueError(f"invalid weekday: {weekday}")
    if not 1 <= month <= 12:
        raise ValueError(f"invalid month: {month}")

    return f"{weekdays[weekday]}, {day:02d} {months[month]} {year:04d} {hour:02d}:{minute:02d}:{second:02d}"


def get_available_path(path):
    path = Path(path)

    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    i = 2
    while True:
        new_path = parent / f"{stem} ({i}){suffix}"
        if not new_path.exists():
            return new_path
        i += 1


def main(java_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    adf_paths = [f for f in java_dir.iterdir() if f.suffix.lower() == ".adf"]
    config = CONFIGS["D505i"]

    for adf_path in adf_paths:
        print(f"\n[{adf_path.name}]")
        try:
            app_id = adf_path.stem
            jar_path = adf_path.parent / (app_id + ".jar")
            sp_path = adf_path.parent / (app_id + ".scr")
            if not os.path.exists(jar_path):
                print(f"Failed: No JAR file found.")
                continue

            with open(adf_path, "rb") as inf:
                adf_data = inf.read()

            if os.path.exists(sp_path):
                with open(sp_path, "rb") as inf:
                    sp_data = inf.read()
            else:
                sp_data = bytearray()
                print(f"WARN: No SP file found for {adf_path.name}")

            jam_out_data, sp_out_data, org_app_name = convert(adf_data, sp_data, config)

            org_app_name = org_app_name or app_id

            jam_out_path = get_available_path(os.path.join(out_dir, f'{org_app_name}.jam'))
            jar_out_path = get_available_path(os.path.join(out_dir, f'{org_app_name}.jar'))
            sp_out_path = get_available_path(os.path.join(out_dir, f'{org_app_name}.sp'))
                
            with open(jam_out_path, 'wb') as outf:
                outf.write(jam_out_data)

            shutil.copy(jar_path, jar_out_path)

            with open(sp_out_path, 'wb') as outf:
                outf.write(sp_out_data)

            print(f"Successfully processed! -> {org_app_name}")
        except Exception as e:
            traceback.print_exc()
    print(f"\nAll done! => {out_dir}")


def parse_text(offset, data):
    if data[offset] == 0:
        return None
    else:
        end = data.find(b"\x00", offset)
        return data[offset:end].decode("cp932")


def to_jam_str(adf_dict):
    ret = ""
    for key, value in adf_dict.items():
        ret += f"{key} = {value}\n"
    
    ret += f"UseNetwork = http\n"
    ret += f"UseBrowser = launch\n"

    return ret


def to_org_app_name(package_url):
    if m := re.match(r'(?:.+?([^\r\n\/:*?"><|=]+)\.jar)+', package_url):
        ret = m[1]
    else:
        ret = None

    return ret



def convert(adf_data, sp_data, config):
    adf_dict = perse_adf(adf_data, config)
    jam_str = to_jam_str(adf_dict)
    
    jam_out_data = jam_str.encode("cp932", errors="replace")
    sp_out_data = add_header_to_sp(jam_str, sp_data)

    org_app_name = to_org_app_name(adf_dict["PackageURL"])

    return (jam_out_data, sp_out_data, org_app_name)


def parse_spsizes(adf_data, start_offset, endian="little", single=False):
    sp_sizes = []
    off = start_offset
    adf_size = len(adf_data)

    if endian == "little":
        parse_str = "<I"
    else:
         parse_str = ">I"

    if single:
        sp_sizes = [struct.unpack(parse_str, adf_data[off : off + 4])[0]]
    else:
        while True:
            sp_size = struct.unpack(parse_str, adf_data[off : off + 4])[0]

            if sp_size == 0xFFFFFFFF:
                break

            sp_sizes.append(sp_size)
            off += 4

            if off > adf_size:
                raise ValueError("out of bounds of the SP file")

            if len(sp_sizes) > 16:
                raise ValueError("exceeded 16 partition")

    return sp_sizes


def perse_adf(adf_data, config):
    adf_dict = {}

    if config["sp_type"] == SpType.SINGLE:
        sp_sizes = parse_spsizes(adf_data, config["sp_size_off"], "big", True)
    else:
        sp_sizes = parse_spsizes(adf_data, config["sp_size_off"], "big")

    if len(sp_sizes) > 0:
        adf_dict["SPsize"] = ",".join([str(s) for s in sp_sizes])
    
    if (text := parse_text(config["package_url_off"], adf_data)) is not None:
        adf_dict["PackageURL"] = text

    if (text := parse_text(config["app_name_off"], adf_data)) is not None:
        adf_dict["AppName"] = text

    if (text := parse_text(config["app_ver_off"], adf_data)) is not None:
        adf_dict["AppVer"] = text

    if (text := parse_text(config["kvm_ver_off"], adf_data)) is not None:
        adf_dict["KvmVer"] = text

    if (text := parse_text(config["profile_ver_off"], adf_data)) is not None:
        adf_dict["ProfileVer"] = text

    if (text := parse_text(config["app_class_off"], adf_data)) is not None:
        adf_dict["AppClass"] = text

    if (text := parse_text(config["app_param_off"], adf_data)) is not None:
        adf_dict["AppParam"] = text

    if (text := parse_text(config["target_device_off"], adf_data)) is not None:
        adf_dict["TargetDevice"] = text

    adf_dict["LastModified"] = parse_datetime(
        adf_data[config["last_modified_off"] : config["last_modified_off"] + 8]
    )

    jar_size = int.from_bytes(adf_data[config["app_size_off"] : config["app_size_off"] + 4], "big")
    adf_dict["AppSize"] = str(jar_size)
    adf_dict["DrawArea"] = config["draw_area"]

    print(f"{adf_dict=}")
    return adf_dict


def add_header_to_sp(jam_str, sp_data):
    def create_header_sp(sp_sizes):
        header = bytearray()
        for size in sp_sizes:
            header += size.to_bytes(4, byteorder="little")
        header += b"\xFF" * (0x40 - len(header))
        
        return header + sp_data

    if m := re.search(r'SPsize\s*=\s*([\d,]+)', jam_str):
        sp_size_str = m.group(1)
        sp_sizes = [int(size) for size in sp_size_str.split(',')]
        return create_header_sp(sp_sizes)
    else:
        return create_header_sp([0])



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("java_dir")
    parser.add_argument("-o", "--out-dir", default=None)
    args = parser.parse_args()

    java_dir = Path(args.java_dir)
    out_dir = Path(args.out_dir or os.path.join(java_dir.parent, "java_converted"))

    main(java_dir, out_dir)