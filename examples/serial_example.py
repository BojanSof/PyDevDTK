import time

from pydevdtk.coms.serial import Serial


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


ser = Serial()
com_ports = ser.get_found_devices()
print(f"Found ports: {com_ports}\n")

port = input("Type in the port to read the data from: ")
if port not in com_ports:
    print(f"Requested port {port} not found")

ser.open(port)

t_run = 10
t_start = time.time()
parser = Parser()
while time.time() - t_start < t_run:
    for sin, cos in parser.parse_data(ser.get_data_event()):
        print(f"sin = {sin} | cos = {cos}")

ser.close()
