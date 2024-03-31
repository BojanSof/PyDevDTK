import serial
import serial.tools.list_ports as ports


class Serial:
    def __init__(self):
        self.port = None

    def get_found_devices(self) -> list[str]:
        com_ports = ports.comports()
        return [com_port.device for com_port in com_ports]

    def open(self, port: str, baudrate: int = 9600):
        self.port = serial.Serial(port=port, baudrate=baudrate)
        if not self.port.is_open:
            return False
        else:
            return True

    def close(self) -> True:
        if self.port.is_open:
            self.port.close()
            return True
        else:
            return False
