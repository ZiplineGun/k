import os
import sys
import glob

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
        
    # try:
    #     data.decode("cp932")
    #     return "txt"
    # except:
    #     pass

    return None

if __name__ == "__main__":
    dirpath = sys.argv[1]
    if os.path.isdir(dirpath):
        for file in glob.glob(os.path.join(dirpath, "*")):
            if os.path.isdir(file): continue
            with open(file, "rb") as inf:
                extention = detect_extension(inf.read(0x30))
            if extention is not None:
                os.rename(file, os.path.splitext(file)[0] + "." + extention)
                print(f"{os.path.basename(file)} => {extention}")