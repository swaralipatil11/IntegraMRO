import urllib.request
import bz2
import os

url = "http://ciscobinary.openh264.org/openh264-1.8.0-win64.dll.bz2"
output_dll = "openh264-1.8.0-win64.dll"

try:
    print("Downloading openh264 DLL from Cisco...")
    urllib.request.urlretrieve(url, "openh264.dll.bz2")
    
    print("Decompressing bz2 archive...")
    with bz2.open("openh264.dll.bz2", "rb") as source, open(output_dll, "wb") as dest:
        dest.write(source.read())
        
    print("Cleanup temporary bz2 file...")
    os.remove("openh264.dll.bz2")
    print("Successfully downloaded and extracted openh264-1.8.0-win64.dll!")
except Exception as e:
    print(f"Error occurred: {e}")
