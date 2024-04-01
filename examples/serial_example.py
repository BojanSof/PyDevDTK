import time

from pydevdtk.coms.serial import Serial

ser = Serial()
com_ports = ser.get_found_devices()
print(f"Found ports: {com_ports}\n")

port = input("Type in the port to read the data from: ")
if port not in com_ports:
    print(f"Requested port {port} not found")

ser.open(port)

t_run = 10
t_start = time.time()
sin = []
cos = []
data = bytearray()
while time.time() - t_start < t_run:
    print(ser.get_data_event().decode("ascii"))

ser.close()
