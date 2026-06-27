import os
import sys
import glob
from concurrent.futures import ThreadPoolExecutor

def detect_extension(data):
    if data[:4] == b"\x50\x4B\x03\x04":
        return "jar"
    elif (
        (data[:4] == b"\xff\xd8\xff\xe0" and data[6:10] == b"JFIF") or
        (data[:4] == b"\xff\xd8\xff\xe1" and data[6:10] == b"Exif") or
        data[:4] == b"\xFF\xD8\xFF\xDB" or
        data[:4] == b"\xFF\xD8\xFF\xEE"
    ):
        return "jpg"
    elif data[:4] == b"melo":
        return "mld"
    elif data[:4] == b"MMMD":
        return "mmf"
    elif data.find(b"MIDlet-Name:") != -1:
        return "jad"
    elif data[:3] in [b"CWS", b"FWS", b"ZWS"]:
        return "swf"
    elif data[:6] in [b"GIF89a", b"GIF87a"]:
        return "gif"
    elif data[:4] == b"\x89\x50\x4E\x47":
        return "png"
    elif data[4:8] == b"ftyp":
        return "3gp"
    elif data[257:262] == b"ustar":
        return "tar"
    elif data[:4] == b"RIFF" and data[8:0x10] == b"QLCMfmt ":
        return "qcp"

    # try:
    #     data.decode("cp932")
    #     return "txt"
    # except:
    #     pass

    return None
    

def process(file):
    with open(file, "rb") as f:
        data = f.read(262)
    ext = detect_extension(data)
    if ext:
        os.rename(file, os.path.splitext(file)[0] + "." + ext)
        print(f"{os.path.basename(file)} => {ext}")


if __name__ == "__main__":
    dirpath = sys.argv[1]
    with ThreadPoolExecutor() as ex:
        ex.map(process, [e.path for e in os.scandir(dirpath) if e.is_file()])
