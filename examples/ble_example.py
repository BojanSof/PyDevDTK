import sys
import time
import queue

from pydevdtk.coms.ble import Ble


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
time.sleep(2)
ble.stop_scan()

ble_devs = ble.get_found_devices()
ble_devs = [ble_dev for ble_dev in ble_devs if len(str(ble_dev)) > 0]
ble_devs_names = [
    str(ble_dev) for ble_dev in ble_devs if len(str(ble_dev)) > 0
]

print(f"Found devs: {ble_devs_names}\n")

dev_name = input("Type in the BLE dev name to read the data from: ")
if dev_name not in ble_devs_names:
    print(f"Requested device {dev_name} not found")
    sys.exit(1)

# wait for connection to establish
dev = ble_devs[ble_devs_names.index(dev_name)]
print(f"Connecting to {dev}...")
t_timeout = 5
ble.connect(dev)
t_start = time.time()
while time.time() - t_start < t_timeout:
    if ble.is_connected(dev):
        break
    else:
        time.sleep(0.2)
if not ble.is_connected(dev):
    print(f"Could not connect to device {dev}")
    sys.exit(1)

print(f"Connected to {dev}")

data_queue = queue.Queue()
parser = Parser()
ble.start_notifications(
    dev,
    "beb5483e-36e1-4688-b7f5-ea07361b26a8",
    lambda data: data_queue.put(data),
)
print("Notifications started")

t_run = 10
t_start = time.time()
while time.time() - t_start < t_run:
    data = data_queue.get()
    for sin, cos in parser.parse_data(data):
        print(f"sin = {sin} | cos = {cos}")

ble.stop_notifications(
    dev,
    "beb5483e-36e1-4688-b7f5-ea07361b26a8",
)
print("Notifications stopped")

print(f"Disconnecting from {dev}...")
ble.disconnect(dev)
t_timeout = 5
t_start = time.time()
while time.time() - t_start < t_timeout:
    if not ble.is_connected(dev):
        break
if ble.is_connected(dev):
    print(f"Could not disconnect from device {dev}")
    sys.exit(2)
print(f"Disconnected from {dev}")
