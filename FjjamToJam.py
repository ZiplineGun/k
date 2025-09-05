import os
import datetime
import sys
import re

fjjam_data_dir = sys.argv[1]
outdir = os.path.join(fjjam_data_dir, "output_jam")
os.makedirs(outdir, exist_ok=True)

for i in range(500): 
    num = f"{i:04}"

    if not os.path.isfile(os.path.join(fjjam_data_dir, f"{num}_appName.dat")):
        continue
    print(f"\n[{num}]")

    jam_dict = {}

    jam_filename = ""
    filepath = os.path.join(fjjam_data_dir, f"{num}_jamFileName.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            jam_filename = file.read().decode("utf16")

    jar_filename = ""
    filepath = os.path.join(fjjam_data_dir, f"{num}_jarFileName.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            jar_filename = file.read().decode("utf16")

    sp_dir = os.path.dirname(jar_filename)

    print(f"Jam Path: {jam_filename}") # Sometimes it doesn't exist.
    print(f"Jar Path: {jar_filename}")
    print(f"SP Dir: {sp_dir}") # filename: sp0, sp1...

    filename = re.sub(r"\.jar", "", os.path.basename(jar_filename), flags=re.IGNORECASE)

    # Required
    filepath = os.path.join(fjjam_data_dir, f"{num}_appName.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            jam_dict["AppName"] = file.read().decode("cp932")

    filepath = os.path.join(fjjam_data_dir, f"{num}_packageUrl.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            jam_dict["PackageURL"] = file.read().decode("cp932")

    filepath = os.path.join(fjjam_data_dir, f"{num}_jar_Size.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            jam_dict["AppSize"] = str(int.from_bytes(file.read()[0:4], "little"))

    filepath = os.path.join(fjjam_data_dir, f"{num}_appClass.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            jam_dict["AppClass"] = file.read().decode("cp932")

    filepath = os.path.join(fjjam_data_dir, f"{num}_lastModifiedTime.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            datedata = file.read()[0:4]
            if datedata == b"\x00\x00\x00\x00":
                jam_dict["LastModified"] = "Mon, 01 Jun 2000 00:00:00"
            else:
                timestamp = int.from_bytes(datedata, "big")
                dt = datetime.datetime.fromtimestamp(timestamp, datetime.UTC)
                formatted_date = dt.strftime("%a, %d %b %Y %H:%M:%S")
                jam_dict["LastModified"] = formatted_date


    required_keys = ["AppName", "PackageURL", "AppSize", "AppClass", "LastModified"]
    missing_keys = [key for key in required_keys if key not in jam_dict]
    if missing_keys:
        print(f"Missing required keys: {', '.join(missing_keys)}")




    # Optional
    filepath = os.path.join(fjjam_data_dir, f"{num}_appVersion.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            jam_dict["AppVer"] = file.read().decode("cp932")

    spsizes = []
    for j in range(15):
        filepath = os.path.join(fjjam_data_dir, f"{num}_spSize{j}.dat")
        if os.path.isfile(filepath):
            with open(filepath, "rb") as file:
                spsize = int.from_bytes(file.read()[0:4], "little")
                if spsize  == 0xFF_FF_FF_FF:
                    break
                else:
                    spsizes.append(str(spsize))
    if spsizes:
        jam_dict["SPsize"] = ",".join(spsizes)

    filepath = os.path.join(fjjam_data_dir, f"{num}_appParam.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            jam_dict["AppParam"] = file.read().decode("cp932")

    heightpath = os.path.join(fjjam_data_dir, f"{num}_drawAreaHeight.dat")
    widthpath = os.path.join(fjjam_data_dir, f"{num}_drawAreaWidth.dat")
    if os.path.isfile(heightpath) and os.path.isfile(widthpath):
        with open(heightpath, "rb") as heightfile, open(widthpath, "rb") as widthfile:
            height = str(int.from_bytes(heightfile.read()[0:4], "little"))
            width = str(int.from_bytes(widthfile.read()[0:4], "little"))
            if "0" not in [height, width]:
                jam_dict["DrawArea"] = f"{height}x{width}"


    filepath = os.path.join(fjjam_data_dir, f"{num}_profileVersion.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            jam_dict["ProfileVer"] = file.read().decode("cp932")

    filepath = os.path.join(fjjam_data_dir, f"{num}_targetDevice.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            jam_dict["TargetDevice"] = file.read().decode("cp932")

    filepath = os.path.join(fjjam_data_dir, f"{num}_kvmVersion.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            jam_dict["KvmVer"] = file.read().decode("cp932")

    filepath = os.path.join(fjjam_data_dir, f"{num}_networkValid.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            if file.read()[0] == 1: jam_dict["UseNetwork"] = "http"

    filepath = os.path.join(fjjam_data_dir, f"{num}_myConciergeValid.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            if file.read()[0] == 1: jam_dict["MyConcierge"] = "Yes"

    filepath = os.path.join(fjjam_data_dir, f"{num}_useTelephone.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            if file.read()[0] == 1: jam_dict["useTelephone"] = "call"

    filepath = os.path.join(fjjam_data_dir, f"{num}_useBrowser.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            if file.read()[0] == 1: jam_dict["useBrowser"] = "launch"

    filepath = os.path.join(fjjam_data_dir, f"{num}_allowLaunchUrl.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            jam_dict["LaunchByBrowser"] = file.read().decode("cp932")

    filepath = os.path.join(fjjam_data_dir, f"{num}_allowLaunchMail.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            jam_dict["LaunchByMail"] = file.read().decode("cp932")

    filepath = os.path.join(fjjam_data_dir, f"{num}_appTrace.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            if file.read()[0] == 1: jam_dict["AppTrace"] = "on"

    filepath = os.path.join(fjjam_data_dir, f"{num}_getSysInfoValid.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            if file.read()[0] == 1: jam_dict["GetSysInfo"] = "Yes"

    filepath = os.path.join(fjjam_data_dir, f"{num}_accessUserInfo.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            if file.read()[0] == 1: jam_dict["AccessUserInfo"] = "Yes"

    filepath = os.path.join(fjjam_data_dir, f"{num}_messageCode.dat")
    if os.path.isfile(filepath):
        with open(filepath, "rb") as file:
            jam_dict["MessageCode"] = file.read().decode("utf16")



    print(jam_dict)

    with open(os.path.join(outdir, f"{filename}.jam"), "w", encoding="cp932") as file:
        file.write("\n".join(f"{jam[0]} = {jam[1]}" for jam in jam_dict.items()) + "\n")

print(f"\noutput -> {outdir}")
