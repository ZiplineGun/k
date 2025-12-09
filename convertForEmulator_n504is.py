import re
import sys
import os
import struct
import shutil
import email.utils
import traceback
from enum import Enum, auto
import argparse
import copy

class SpType(Enum):
    SINGLE = auto()
    MULTI = auto()

CONFIGS = {
    "N504iS": {
        "device_name": "N504iS",
        "draw_area": "160x180",
        "sp_type": SpType.SINGLE,
        "start_spsize": 0x5C,
        "start_adf": 0x6C,
    },
    "N505iS": {
        "device_name": "N505iS",
        "draw_area": "240x240",
        "sp_type": SpType.MULTI,
        "start_spsize": 0x8C,
        "start_adf": 0xD4,
    },
    "N506i": {
        "device_name": "N506i",
        "draw_area": "240x270",
        "sp_type": SpType.MULTI,
        "start_spsize": 0x8C,
        "start_adf": 0xD4,
    },
    "N506iS": {
        "device_name": "N506iS",
        "draw_area": "240x270",
        "sp_type": SpType.MULTI,
        "start_spsize": 0x8C,
        "start_adf": 0xD4,
    },
}

class DirType(Enum):
    SSR200 = auto()
    M4 = auto()

def detect_dirtype(dir_path):
    if all(os.path.isdir(os.path.join(dir_path, n)) for n in ["ADF", "JAR", "SCP"]):
        return DirType.SSR200
    
    if any(f.startswith("region_") for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))):
        return DirType.M4
    
    raise ValueError("unknown dir type")


def main(model_config, input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    app_path_conbos = []

    dirtype = detect_dirtype(input_dir)
    print("dir type:", dirtype)

    if dirtype == DirType.M4:
        region_files = [file for file in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, file)) and file.startswith("region_")]
        region_files.sort()

        app_path_conbo = {
            "jar": None,
            "sp": None,
            "adf": None,
        }
        # order: JAR [SP] ADF
        for region_file in region_files:
            region_path = os.path.join(input_dir, region_file)
            with open(region_path, "rb") as inf:
                region_data = inf.read()

            if app_path_conbo["jar"] is None and region_data[:4] == b"PK\x03\x04":
                app_path_conbo["jar"] = region_path
            elif app_path_conbo["jar"] is not None and app_path_conbo["sp"] is None:
                try:
                    (adf_dict, _, _) = perse_adf(region_data, model_config["start_adf"])

                    #print(adf_dict)
                    if not all(key in adf_dict for key in ["AppName", "PackageURL", "AppClass", "LastModified"]):
                        raise Exception("Missing required value.")
                    if not adf_dict["PackageURL"].startswith("http://"):
                        raise Exception("PackageURL is not URL")
                    
                    app_path_conbo["adf"] = region_path
                except Exception as e:
                    app_path_conbo["sp"] = region_path
                    #print(region_file, e)
            elif app_path_conbo["jar"] is not None and app_path_conbo["sp"] is not None:
                app_path_conbo["adf"] = region_path
            
            if app_path_conbo["adf"] is not None:
                app_path_conbos.append(copy.deepcopy(app_path_conbo))
                app_path_conbo = {
                    "jar": None,
                    "sp": None,
                    "adf": None,
                }

    elif dirtype == DirType.SSR200:
        adf_dir = os.path.join(input_dir, "ADF")
        jar_dir = os.path.join(input_dir, "JAR")
        scp_dir = os.path.join(input_dir, "SCP")

        for adfname in [f for f in os.listdir(adf_dir) if os.path.join(adf_dir, f)]:
            app_path_conbo = {
                "jar": None,
                "sp": None,
                "adf": None,
            }
            basename = os.path.splitext(adfname)[0]
            app_path_conbo["adf"] = os.path.join(adf_dir, adfname)

            jar_candidate = os.path.join(jar_dir, basename + ".jar")
            if os.path.isfile(jar_candidate):
                app_path_conbo["jar"] = jar_candidate
            else:
                continue

            sp_candidate = os.path.join(scp_dir, basename + ".scp")
            if os.path.isfile(sp_candidate):
                app_path_conbo["sp"] = sp_candidate

            app_path_conbos.append(copy.deepcopy(app_path_conbo))

    else:
        raise ValueError(dirtype)


    for app_path_conbo in app_path_conbos:
        jar_path = app_path_conbo["jar"]
        sp_path = app_path_conbo["sp"]
        adf_path = app_path_conbo["adf"]

        print(f"\n[{os.path.basename(adf_path)}]")
        print(f"ADF: {adf_path}")
        print(f"JAR: {jar_path}")
        print(f"SP: {sp_path}")
        
        try:
            if sp_path is None:
                print(f"WARN: No SP file found for {os.path.basename(adf_path)}")
                sp_data = b""
            else:
                with open(sp_path, "rb") as file:
                    sp_data = file.read()

            with open(jar_path, "rb") as file:
                jar_data = file.read()

            with open(adf_path, "rb") as file:
                adf_data = file.read()

            jar_size = len(jar_data)

            out_adf_data, out_sp_data, jar_name = convert(adf_data, sp_data, jar_size, model_config)

            i = 1
            if os.path.exists(os.path.join(output_dir, f"{jar_name}.jam")):
                while os.path.exists(os.path.join(output_dir, f"{jar_name} ({i}).jam")):
                    i += 1
                jar_name = f"{jar_name} ({i})"

            out_jam_file_path = os.path.join(output_dir, f'{jar_name}.jam')
            out_jar_file_path = os.path.join(output_dir, f'{jar_name}.jar')
            out_sp_file_path = os.path.join(output_dir, f'{jar_name}.sp')
                
            with open(out_jam_file_path, 'wb') as adf_file:
                adf_file.write(out_adf_data)

            shutil.copy(jar_path, out_jar_file_path)

            if sp_path is not None:
                with open(out_sp_file_path, 'wb') as sp_file:
                    sp_file.write(out_sp_data)

            print(f"Output file name: {jar_name}")
        except Exception as e:
            traceback.print_exc()
    print(f"\nAll done! => {output_dir}")


def convert(adf_data, sp_data, jar_size, model_config):
    sp_type = model_config["sp_type"]
    start_spsize = model_config["start_spsize"]
    start_adf = model_config["start_adf"]
    draw_area = model_config["draw_area"]
    device_name = model_config["device_name"]
    
    try:
        if sp_type == SpType.MULTI:
            sp_sizes = read_spsizes_from_adf(adf_data, start_spsize)
        elif sp_type == SpType.SINGLE:
            sp_sizes = [struct.unpack('<I', adf_data[start_spsize:start_spsize + 4])[0]]
            if sp_sizes[0] == 0:
                sp_sizes = []
        else:
            raise Exception("no sp_type input")
    except struct.error:
        print("Failed: bronken ADF file.")
        return

    (adf_dict, jam_download_url, other_items) = perse_adf(adf_data, start_adf)
    print(f"ADF Values: {adf_dict}")
    print(f"JAM unused values: {other_items}")
    print(f"JAM Download URL: {jam_download_url}")

    if len(sp_sizes) != 0 and sum(sp_sizes) != len(sp_data):
        print("WARN: Mismatch between spsize and actual size.")

    if not "DrawArea" in adf_dict:
        print("INFO: Since the ADF does not have a 'DrawArea' value, the device canvas size is used instead.")
        adf_dict["DrawArea"] = draw_area

    # Re-format LastModified
    adf_dict["LastModified"] = email.utils.parsedate_to_datetime(adf_dict["LastModified"])
    adf_dict["LastModified"] = format_last_modified(adf_dict["LastModified"])

    # Create a jam
    jam_str = ""
    for key, value in adf_dict.items():
        jam_str += f"{key} = {value}\n"

    jam_str += f"AppSize = {jar_size}\n"
    
    if 0 < len(sp_sizes) <= 16:
        jam_str += f"SPsize = {','.join(map(str, sp_sizes))}\n"
    else:
        print("WARN: SPsize detection failed.")
    
    jam_str += f"UseNetwork = http\n"
    jam_str += f"UseBrowser = launch\n"

    new_adf_data = jam_str.encode("cp932")

    new_sp_data = add_header_to_sp(jam_str, sp_data)

    if m := re.match(r'(?:.+?([^\r\n\/:*?"><|=]+)\.jar)+', adf_dict["PackageURL"]):
        jar_name = m[1]
    else:
        jar_name = ""

    return (new_adf_data, new_sp_data, jar_name)


def read_spsizes_from_adf(adf_data, start_offset):
    integers = []
    offset = start_offset

    while True:
        integer = struct.unpack('<I', adf_data[offset:offset + 4])[0]

        if integer == 0xFFFFFFFF:
            break

        integers.append(integer)
        offset += 4

    return integers


def perse_adf(adf_data, start_adf):
    adf_dict = {}

    # Parse adf. order: AppName [AppVer] PackageURL [ConfigurationVer] AppClass [AppParam] LastModified [TargetDevice] [ProfileVer] jar_download_url
    adf_items = filter(None, adf_data[start_adf:].split(b"\00"))
    adf_items = list(map(lambda b: b.decode("cp932", errors="replace"), adf_items))

    adf_dict["AppName"] = adf_items[0]

    if not adf_items[1].startswith("http"):
        adf_dict["AppVer"] = adf_items[1]
    else:
        adf_items.insert(1, None)

    adf_dict["PackageURL"] = adf_items[2]
    
    if adf_items[3] in ["CLDC-1.1", "CLDC-1.0"]:
        adf_dict["ConfigurationVer"] = adf_items[3]
    else:
        adf_items.insert(3, None)

    adf_dict["AppClass"] = adf_items[4]

    if not adf_items[5].startswith(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
        adf_dict["AppParam"] = adf_items[5]
    else:
        adf_items.insert(5, None)

    adf_dict["LastModified"] = adf_items[6]

    other_items = []
    jam_download_url = None
    if len(adf_items) > 6:
        for adf_item in adf_items[7:]:
            if re.search(r"(SH|SO|F|D|N|P)\d{3}", adf_item):
                adf_dict["TargetDevice"] = adf_item
            elif adf_item.startswith(("DoJa-1.0", "DoJa-2.0", "DoJa-2.1", "DoJa-2.2", "DoJa-3.0", "DoJa-3.5", "DoJa-4.0", "DoJa-4.1", "DoJa-5.0", "DoJa-5.1")):
                adf_dict["ProfileVer"] = adf_item
            elif adf_item.startswith("http"):
                jam_download_url = adf_item
            elif adf_item.endswith(".gif"):
                adf_dict["AppIcon"] = adf_item
            elif m := re.search(r"\d{3}x\d{3}", adf_item):
                adf_dict["DrawArea"] = m.group(0)
            else:
                other_items.append(adf_item)

    return (adf_dict, jam_download_url, other_items)


def add_header_to_sp(jam_str, sp_datas):
    def create_header_sp(sp_sizes):
        header = bytearray()
        for size in sp_sizes:
            header += size.to_bytes(4, byteorder='little')
        while len(header) < 64:
            header += bytes([255])
        return header

    sp_size_match = re.search(r'SPsize\s*=\s*([\d,]+)', jam_str)
    if sp_size_match:
        sp_size_str = sp_size_match.group(1)
        sp_sizes = [int(size) for size in sp_size_str.split(',')]
        header = create_header_sp(sp_sizes)
    else:
        header = create_header_sp([0])

    return header + sp_datas


def format_last_modified(last_modified_dt):
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    weekday_name = weekdays[last_modified_dt.weekday()]
    month_name = months[last_modified_dt.month - 1]

    last_modified_str = last_modified_dt.strftime(f"{weekday_name}, %d {month_name} %Y %H:%M:%S")
    return last_modified_str


if __name__ == "__main__":
    parser = argparse.ArgumentParser("NEC mova's JAVA converter for idkdoja")
    parser.add_argument("input")
    parser.add_argument("model", choices=CONFIGS.keys(), help="input model")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    output = args.output or os.path.join(os.path.dirname(args.input), "java_output")
    main(CONFIGS[args.model], args.input, output)
