import threading
from typing import Callable

import serial
import serial.tools.list_ports as ports


class Serial:
    def __init__(self):
        self.port = None
        self.data_thread_stop_event = threading.Event()
        self.data_thread = None
        self.on_data = None

    def get_found_devices(self) -> list[str]:
        com_ports = ports.comports()
        return [com_port.device for com_port in com_ports]

    def open(
        self, port: str, on_data: Callable[[bytes], None], **port_kwargs
    ) -> bool:
        self.port = serial.Serial(port=port, **port_kwargs)
        if not self.port.is_open:
            self.port = None
            return False
        else:
            self.on_data = on_data
            self.data_thread = threading.Thread(
                target=self._data_read,
                args=(self.port, self.data_thread_stop_event),
            )
            self.data_thread.start()
            return True

    def close(self) -> bool:
        if self.port is not None:
            self.data_thread_stop_event.set()
            self.data_thread.join()
            self.port.close()
            self.port = None
            self.on_data = None
            return True
        return False

    def is_open(self) -> bool:
        if self.port is not None:
            return self.port.is_open
        return False

    def _data_read(self, port: serial.Serial, stop_event: threading.Event):
        while not stop_event.is_set() and port.is_open:
            data = port.read_all()
            if len(data) > 0:
                self.on_data(data)
