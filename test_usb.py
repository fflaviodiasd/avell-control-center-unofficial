import usb.core
device = usb.core.find(idVendor=0x048d, idProduct=0x600b)
print("Device found:", device is not None)
