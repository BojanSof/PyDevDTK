import threading
import queue

import serial
import serial.tools.list_ports as ports


class Serial:
    def __init__(self):
        self.port = None
        self.data_thread_stop_event = threading.Event()
        self.data_thread = None
        self.data_queue = queue.Queue()

    def get_found_devices(self) -> list[str]:
        com_ports = ports.comports()
        return [com_port.device for com_port in com_ports]

    def open(self, port: str, baudrate: int = 9600) -> bool:
        self.port = serial.Serial(port=port, baudrate=baudrate)
        if not self.port.is_open:
            self.port = None
            return False
        else:
            self.data_thread = threading.Thread(
                target=self._data_read,
                args=(self.port, self.data_queue, self.data_thread_stop_event),
            )
            self.data_thread.start()
            return True

    def close(self) -> bool:
        if self.port is not None and self.port.is_open:
            self.data_thread_stop_event.set()
            self.data_thread.join()
            self.port.close()
            self.port = None
            return True
        return False

    def is_open(self) -> bool:
        if self.port is not None:
            return self.port.is_open
        return False

    def get_data_event(self, block=True, timeout=None):
        try:
            return self.data_queue.get(block, timeout)
        except queue.Empty:
            return None

    def _data_read(
        self, port: serial.Serial, data_queue, stop_event: threading.Event
    ):
        while not stop_event.is_set() and port.is_open:
            data = port.read_all()
            if len(data) > 0:
                data_queue.put(data)
