import threading
from typing import Callable

import serial
import serial.tools.list_ports as ports


class Serial:
    """
    A class that provides a high-level interface for working with serial ports.

    The `Serial` class allows you to open a serial port connection, read and
    write data, and close the connection. It also provides a callback
    mechanism for handling received data.
    """

    def __init__(self):
        """
        Initializes a new instance of the Serial class.
        """
        self.port = None
        self.data_thread_stop_event = threading.Event()
        self.data_thread = None
        self.on_data = None

    def get_found_devices(self) -> list[str]:
        """
        Returns a list of strings representing the device names of all the
        available COM ports.

        Returns
        -------
        list[str]
            A list of strings representing the device names of all the
            available COM ports.
        """
        com_ports = ports.comports()
        return [com_port.device for com_port in com_ports]

    def open(
        self, port: str, on_data: Callable[[bytes], None], **port_kwargs
    ) -> bool:
        """
        Opens a serial port connection and starts a new thread to continuously
        read data from the port.

        Parameters
        ----------
        port : str
            The name of the serial port to open.
        on_data : Callable[[bytes], None]
            A callback function that will be called whenever new data is
            received from the serial port.
        **port_kwargs
            Additional keyword arguments to pass to the `serial.Serial`
            constructor, such as baud_rate, parity, etc. Check the
            `serial.Serial` documentation for more information.

        Returns
        -------
        bool
            True if the serial port was successfully opened, False otherwise.
        """
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
        """
        Closes the serial port if it is open.

        Returns
        -------
        bool
            True if the serial port was successfully closed, False otherwise.
        """
        if self.port is not None:
            self.data_thread_stop_event.set()
            self.data_thread.join()
            self.port.close()
            self.port = None
            self.on_data = None
            return True
        return False

    def is_open(self) -> bool:
        """
        Checks if the serial port is open.

        Returns
        -------
        bool
            True if the serial port is open, False otherwise.
        """
        if self.port is not None:
            return self.port.is_open
        return False

    def _data_read(self, port: serial.Serial, stop_event: threading.Event):
        """
        Continuously reads data from the specified serial port until the stop
        event is set or the port is closed.

        Parameters
        ----------
        port : serial.Serial
            The serial port to read data from.
        stop_event : threading.Event
            The event used to signal when to stop reading data.

        Returns
        -------
        None
        """
        while not stop_event.is_set() and port.is_open:
            data = port.read_all()
            if len(data) > 0:
                self.on_data(data)
