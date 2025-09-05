import argparse
import os
import re
import traceback
import zipfile

def int_with_base(value):
    try:
        return int(value, 0)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid integer.")
        
parser = argparse.ArgumentParser(description="Converts all files in directory")
parser.add_argument("input")
parser.add_argument("output")
parser.add_argument(
    "-x",
    "--header",
    help="Header size.",
    default=0x20,
    type=int_with_base,
)
parser.add_argument(
    "-d",
    "--data",
    help="Data size.",
    default=0x4000,
    type=int_with_base,
)
parser.add_argument(
    "-o",
    "--oob",
    help="Oob size.",
    default=0x2,
    type=int_with_base,
)
# Do not include the 2 byte offset
parser.add_argument(
    "-s",
    "--start_jam",
    help="offset of the jam in the dat. (default:0xD3C, SO903iTV: 0xD44, SO902i, SO702i: 0xDF4, SO905i: 0xF7A, SO906i: 0xF84)",
    default=0xD3C,
    type=int_with_base,
)
parser.add_argument(
    "-f",
    "--footer",
    help="footer size.",
    default=0x13,
    type=int_with_base,
)

args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

# for idkdoja
def add_header_to_sp(jam_str, sp_content):
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

    return header + sp_content
    
    
def remove_oob(content):
    content_ = content[args.header : len(content) - args.footer]
    content_len = len(content_)

    new_content = bytearray()
    for i in range(0, content_len, args.data + args.oob):
        end = min(i + args.data, content_len)
        new_content += content_[i : end]

    return new_content

def main(dats, base_dir):
    for dat_name in dats:
        try:
            base_name = os.path.splitext(dat_name)[0]
            print(f"\n[{base_name}]")
            
            dat_path = os.path.join(base_dir, dat_name)
            jar_path = os.path.join(base_dir, f"{base_name}.jar")
            if not os.path.isfile(jar_path): raise ValueError("no jar")
            scr_path = os.path.join(base_dir, f"{base_name}.scr")
            if not os.path.isfile(scr_path): print("WAMN: no scr")

            with open(dat_path, "rb") as file:
                dat_content = file.read()
            
            if dat_content.find(b"AppName") == -1: raise ValueError("""no "AppName" string in the dat file.""")
            
            start_jam = args.start_jam - 2
            jam_size = 0
            
            # "any" etc may occasionally be inserted, causing the offset to shift.
            for i in range(5):
                start_jam = start_jam + jam_size + 2
                jam_size = int.from_bytes(dat_content[start_jam - 2 : start_jam], "little") - 0x4000
                jam_content = dat_content[start_jam : start_jam + jam_size]
                if jam_size > 0x30: break
            
            jam_str = jam_content.decode("cp932")
            print(jam_str)
            jar_size = int(re.search(r"AppSize\x20*=\x20*([^\r\n]+)", jam_str)[1])
            
            package_url = re.search(r"PackageURL\x20*=\x20*([^\r\n]+)", jam_str)[1]
            if m := re.search(r"""([^\r\n\/:*?"><|=]+)\.jar""", package_url):
                jar_name = m[1]
            else:
                jar_name = ""
            print(f'File name detection: "{jar_name}"')

            with open(jar_path, 'rb') as file:
                jar_content = file.read()
            new_jar_content = remove_oob(jar_content)

            new_sp_content = None
            if os.path.isfile(scr_path): 
                with open(scr_path, 'rb') as file:
                    sp_content = file.read()

                new_sp_content = remove_oob(sp_content)
                if new_sp_content[:0x16] == bytes.fromhex("00 11 80 01 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00 00 00 40"):
                    new_sp_content = new_sp_content[0x16:]
                new_sp_content = add_header_to_sp(jam_str, new_sp_content)
            
            # Check for duplicate files
            while True:
                if not os.path.exists(os.path.join(args.output, f"{jar_name}.jam")): break
                jar_name += "_"
                
            with open(os.path.join(args.output, f"{jar_name}.jam"), 'wb') as file:
                file.write(jam_content)
            with open(os.path.join(args.output, f"{jar_name}.jar"), 'wb') as file:
                file.write(new_jar_content)
            if os.path.isfile(scr_path): 
                with open(os.path.join(args.output, f"{jar_name}.sp"), 'wb') as file:
                    file.write(new_sp_content)
                    
            # Test a JAR extraction
            try:
                zip = zipfile.ZipFile(os.path.join(args.output, f"{jar_name}.jar"))
                zip.extractall("__temp")
            except Exception as e:
                print(f"""!!! WAMN: the jar is corrupted. (Error: "{e}") !!!""")
            finally:
                try:
                    shutil.rmtree("__temp")
                except:
                    pass
        except Exception:
            traceback.print_exc()
        
        

dats = [dat_path for dat_path in os.listdir(args.input) if dat_path.endswith(".dat")]
main(dats, args.input)

new_dir = os.path.join(args.input, "new")
if os.path.isdir(new_dir):
    new_dats = [dat_path for dat_path in os.listdir(new_dir) if dat_path.endswith(".dat")]
    main(new_dats, new_dir)
    
old_dir = os.path.join(args.input, "old")
if os.path.isdir(old_dir):
    old_dats = [dat_path for dat_path in os.listdir(old_dir) if dat_path.endswith(".dat")]
    main(old_dats, old_dir)
