import sys
import time

from pydevdtk.coms.ble import Ble, BleStatus


class Parser:
    def __init__(self):
        self.buffer = b""

    def parse_data(self, data):
        self.buffer += data
        lines = self.buffer.split(b"\n")
        self.buffer = lines.pop()

        for line in lines:
            line = line.strip()
            if line:
                values = line.decode("ascii").split(",")
                try:
                    parsed_values = tuple(map(float, values))
                    yield parsed_values
                except ValueError:
                    pass


ble = Ble()
print("Scanning for BLE devices")
ble.start_scan()
time.sleep(5)
ble.stop_scan()

ble_devs = ble.get_found_devices()
ble_devs_names = [ble_dev["name"] for ble_dev in ble_devs]

print(f"Found devs: {ble_devs_names}\n")

dev_name = input("Type in the BLE dev name to read the data from: ")
if dev_name not in ble_devs_names:
    print(f"Requested device {dev_name} not found")

dev = ble_devs[ble_devs_names.index(dev_name)]
# wait for connection to establish
print(f"Connecting to {dev_name}")
ble.connect(dev["dev"])
t_timeout = 5
t_start = time.time()
while time.time() - t_start < t_timeout:
    status = ble.get_status(dev["address"])
    if status is not None and status == BleStatus.Connected:
        break
if not ble.is_connected(dev["address"]):
    print(f"Could not connect to device {dev_name}")
    sys.exit(1)
print(f"Connected to {dev_name}")
ble.start_notifications_characteristic(
    dev["address"], "beb5483e-36e1-4688-b7f5-ea07361b26a8"
)
t_run = 10
parser = Parser()
t_start = time.time()
while time.time() - t_start < t_run:
    addr, uuid, data = ble.get_data_event()
    for sin, cos in parser.parse_data(data):
        print(f"sin = {sin} | cos = {cos}")

ble.disconnect(dev["address"])
t_timeout = 5
t_start = time.time()
while time.time() - t_start < t_timeout:
    status = ble.get_status(dev["address"])
    if status is None:
        break
status = ble.get_status(dev["address"])
if status is not None:
    print(f"Failed to disconnect from {dev_name}")
