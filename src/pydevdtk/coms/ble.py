import asyncio
import enum
import threading
from typing import Callable

from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData


class BleStatus(enum.Enum):
    """Status of the BLE connection."""

    Connecting = enum.auto()
    Connected = enum.auto()
    Disconnecting = enum.auto()


class BleDevice:
    """BLE device advertisement data and connection related objects"""

    def __init__(
        self,
        name: str | None,
        address: str,
        rssi: int,
        uuids: list[str],
        manufacturer_data: dict[int, bytes],
    ):
        """
        Initializes a new instance of the BleDevice class.

        Parameters
        ----------
        name : str or None
            The name of the device. Can be None.
        address : str
            The address of the device.
        rssi : int
            The received signal strength indicator (RSSI) of the device.
        uuids : list of str
            A list of UUIDs associated with the device.
        manufacturer_data : dict of int to bytes
            A dictionary containing manufacturer-specific data.
        """
        self.name = name
        self.address = address
        self.rssi = rssi
        self.uuids = uuids
        self.manufacturer_data = manufacturer_data
        self._device_hndl = None
        self._client = None

    def __str__(self) -> str:
        return self.name if self.name is not None else ""


class BleCharacteristic:
    """BLE characteristic description"""

    def __init__(self, uuid: str, properties: list[str]):
        """
        Initializes a new instance of the BleCharacteristic class.

        Parameters
        ----------
        uuid : str
            The UUID of the characteristic.
        properties : list of str
            The properties of the characteristic, which can be one or more of:
            'read', 'write', 'write-without-response', 'notify' or 'indicate'.
        """
        self.uuid = uuid
        self.properties = properties


class BleService:
    """BLE service description"""

    def __init__(self, uuid: str, characteristics: list[BleCharacteristic]):
        """
        Initializes a new instance of the BleService class.

        Parameters
        ----------
        uuid : str
            The UUID of the service.
        characteristics : list of BleCharacteristic
            A list of BleCharacteristic objects representing the
            characteristics of the service.
        """
        self.uuid = uuid
        self.characteristics = characteristics


class Ble:
    """
    A class that allows to utilize the BLE module of the device,
    including scanning for BLE devices, connecting to BLE devices,
    and data operations including read, write and notify.
    """

    def __init__(self):
        """
        Initializes a new instance allowing to utilize the BLE module of the
        device, including scanning for BLE devices, connecting to BLE devices,
        and data operations including read, write and notify.

        Runs asyncio event loop in a separate thread which handles all BLE
        events.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        self.found_devices: dict[str, BleDevice] = {}
        self.on_device: Callable[[BleDevice], None] | None = None
        self.scanning = False
        self.scan_stop_event = asyncio.Event()

        self.on_connect: dict[str, Callable[[], None]] = {}
        self.on_disconnect: dict[str, Callable[[], None]] = {}
        self.status_devices: dict[str, BleStatus] = {}
        self.disconnect_events: dict[str, asyncio.Event] = {}
        self.connected_devices: dict[str, BleDevice] = {}

        self.event_loop = asyncio.new_event_loop()
        self.event_loop_thread = threading.Thread(
            target=self._asyncloop, daemon=True
        )
        self.event_loop_thread.start()

    def __del__(self):
        for dev in self.connected_devices.values():
            self.disconnect(dev)
        self.event_loop.call_soon_threadsafe(self.event_loop.stop)
        self.event_loop_thread.join()

    def start_scan(self, on_device: Callable[[BleDevice], None] | None = None):
        """
        Start scanning for Bluetooth Low Energy (BLE) devices.

        Parameters
        ----------
        on_device : Callable[[BleDevice], None] or None, optional
            Optional callback function to be called when a BLE device is found.
            The callback function should take a `BleDevice` object as its
            parameter.

        Returns
        -------
        None
        """
        self.found_devices = {}  # clear previously found devices
        self.on_device = on_device
        self.scan_stop_event.clear()
        asyncio.run_coroutine_threadsafe(
            self._bluetooth_scan(self.scan_stop_event), self.event_loop
        )
        self.scanning = True

    def stop_scan(self):
        """
        Stops the ongoing Bluetooth Low Energy (BLE) scan if it is currently
        running.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        if self.scanning:
            self.event_loop.call_soon_threadsafe(self.scan_stop_event.set)
            self.scanning = False

    def is_scanning(self) -> bool:
        """
        Returns the scanning status.

        Parameters
        ----------
        None

        Returns
        -------
        bool
            The scanning status (True if scanning, False otherwise).
        """
        return self.scanning

    def get_found_devices(self) -> list[BleDevice]:
        """
        Returns a list of all the found devices during scanning.

        Returns
        -------
        list of BleDevice
            A list of BleDevice objects representing the found devices.
        """
        return list(self.found_devices.values())

    def connect(
        self,
        dev: BleDevice,
        on_connect: Callable[[], None] | None = None,
        on_disconnect: Callable[[], None] | None = None,
    ):
        """
        A method to connect to a BLE device if it is not already connected to
        it.

        Parameters
        ----------
        dev : BleDevice
            The BLE device to connect to.
        on_connect : Callable[[], None] or None, optional
            Callback for when the connection is established. Defaults to None.
        on_disconnect : Callable[[], None] or None, optional
            Callback for when the connection is terminated. Defaults to None.

        Returns
        -------
        None
        """
        if not self.is_connected(dev):
            if on_connect is not None:
                self.on_connect[dev.address] = on_connect
            if on_disconnect is not None:
                self.on_disconnect[dev.address] = on_disconnect
            self.disconnect_events[dev.address] = asyncio.Event()
            self.status_devices[dev.address] = BleStatus.Connecting
            asyncio.run_coroutine_threadsafe(
                self._bluetooth_connect(
                    dev, self.disconnect_events[dev.address]
                ),
                self.event_loop,
            )

    def disconnect(self, dev: BleDevice):
        """
        Disconnects a BLE device if it is currently connected to it.

        Parameters
        ----------
        dev : BleDevice
            The BLE device to disconnect.

        Returns
        -------
        None
        """
        if self.is_connected(dev):
            self.status_devices[dev.address] = BleStatus.Disconnecting
            self.event_loop.call_soon_threadsafe(
                self.disconnect_events[dev.address].set
            )

    def is_connected(self, dev: BleDevice) -> bool:
        """
        Check if a given BLE device is connected.

        Parameters
        ----------
        dev : BleDevice
            The BLE device to check.

        Returns
        -------
        bool
            True if the device is connected, False otherwise.
        """
        return dev.address in self.connected_devices

    def get_connected_devices(self) -> list[BleDevice]:
        """
        Returns a list of all the connected devices.

        Returns
        -------
        list of BleDevice
            A list of BleDevice objects representing the connected devices.
        """
        return list(self.connected_devices.values())

    def get_status(self, dev: BleDevice) -> BleStatus | None:
        """
        Retrieves the status of the connection for a given BLE device.
        Useful to check if the device is in process of establishing
        connection, disconnecting or it is already connected.

        Parameters
        ----------
        dev : BleDevice
            The BLE device for which to retrieve the status.

        Returns
        -------
        BleStatus or None
            The connection status of the device.
        """
        if dev.address in self.status_devices:
            return self.status_devices[dev.address]
        else:
            return None

    def get_services_and_characteristics(
        self, dev: BleDevice
    ) -> list[BleService]:
        """
        Retrieves the list of services and characteristics of a given BLE
        device.

        Parameters
        ----------
        dev : BleDevice
            The BLE device for which to retrieve the services and
            characteristics.

        Returns
        -------
        list of BleService
            A list of BleService objects representing the services and
            characteristics of the device.
            Each BleService object contains the UUID of the service and a list
            of BleCharacteristic objects representing the characteristics of
            the service.
            Returns None if the device is not connected.
        """
        if not self.is_connected(dev):
            services_collection = None
        else:
            services_collection = []
            client = self.connected_devices[dev.address]._client
            for _, service in client.services.services.items():
                service_characteristics = []
                for characteristic in service.characteristics:
                    ble_characteristic = BleCharacteristic(
                        uuid=characteristic.uuid,
                        properties=characteristic.properties,
                    )
                    service_characteristics.append(ble_characteristic)
                ble_service = BleService(
                    uuid=service.uuid, characteristics=service_characteristics
                )
                services_collection.append(ble_service)
        return services_collection

    def read_characteristic(
        self, dev: BleDevice, char_uuid: str
    ) -> bytearray | None:
        """
        Reads the value of a characteristic from a BLE device.

        Parameters
        ----------
        dev : BleDevice
            The BLE device to read from.
        char_uuid : str
            The UUID of the characteristic to read.

        Returns
        -------
        bytearray or None
            The value of the characteristic if it exists and is readable,
            otherwise None.
        """
        if self.is_connected(dev):
            client = self.connected_devices[dev.address]._client
            chars = list(client.services.characteristics.values())
            chars_uuids = [char.uuid for char in chars]
            chars_properties = [char.properties for char in chars]
            if char_uuid in chars_uuids:
                i_char = chars_uuids.index(char_uuid)
                if "read" in chars_properties[i_char]:
                    future = asyncio.run_coroutine_threadsafe(
                        self._bluetooth_read(client, char_uuid),
                        self.event_loop,
                    )
                    return future.result()
        return None

    def write_characteristic(
        self,
        dev: BleDevice,
        char_uuid: str,
        data: bytes | bytearray,
        response: bool,
    ) -> bytearray | None:
        """
        Writes data to a characteristic of a BLE device.

        Parameters
        ----------
        dev : BleDevice
            The BLE device to write to.
        char_uuid : str
            The UUID of the characteristic to write to.
        data : bytes or bytearray
            The data to write.
        response : bool
            Whether to expect a response from the device.

        Returns
        -------
        bytearray or None
            The result of the write operation, or None if the write failed.

        This function checks if the device is connected and if the
        characteristic exists and is writable. If so, it writes the data to
        the characteristic. The result of the write operation is returned.
        If the device is not connected or the characteristic does not exist or
        is not writable, None is returned.
        """
        if self.is_connected(dev):
            client = self.connected_devices[dev.address]._client
            chars = list(client.services.characteristics.values())
            chars_uuids = [char.uuid for char in chars]
            chars_properties = [char.properties for char in chars]
            if char_uuid in chars_uuids:
                i_char = chars_uuids.index(char_uuid)
                prop = "write" if response else "write-without-response"
                if prop in chars_properties[i_char]:
                    future = asyncio.run_coroutine_threadsafe(
                        self._bluetooth_write(
                            client, char_uuid, data, response
                        ),
                        self.event_loop,
                    )
                    return future.result()
        return None

    def start_notifications(
        self,
        dev: BleDevice,
        char_uuid: str,
        on_data: Callable[[bytes | bytearray], None],
    ) -> bool:
        """
        A function to start notifications for a specific characteristic of a
        BLE device.

        Parameters
        ----------
        dev : BleDevice
            The BLE device for which notifications are to be started.
        char_uuid : str
            The UUID of the characteristic for which notifications are to be
            started.
        on_data : Callable[[bytes or bytearray], None]
            The callback function to handle the received notification data.

        Returns
        -------
        bool
            True if notifications were successfully started, False otherwise.
        """
        if self.is_connected(dev):
            client = self.connected_devices[dev.address]._client
            chars = list(client.services.characteristics.values())
            chars_uuids = [char.uuid for char in chars]
            chars_properties = [char.properties for char in chars]
            if char_uuid in chars_uuids:
                i_char = chars_uuids.index(char_uuid)
                if "notify" in chars_properties[i_char]:
                    asyncio.run_coroutine_threadsafe(
                        self._bluetooth_start_notify(
                            client, char_uuid, on_data
                        ),
                        self.event_loop,
                    )
                    return True
        return False

    def stop_notifications(self, dev: BleDevice, char_uuid: str) -> bool:
        """
        A function to stop notifications for a specific characteristic of a
        BLE device.

        Parameters
        ----------
        dev : BleDevice
            The BLE device for which notifications are to be stopped.
        char_uuid : str
            The UUID of the characteristic for which notifications are to be
            stopped.

        Returns
        -------
        bool
            True if notifications were successfully stopped, False otherwise.
        """
        if self.is_connected(dev):
            client = self.connected_devices[dev.address]._client
            chars = list(client.services.characteristics.values())
            chars_uuids = [char.uuid for char in chars]
            chars_properties = [char.properties for char in chars]
            if char_uuid in chars_uuids:
                i_char = chars_uuids.index(char_uuid)
                if "notify" in chars_properties[i_char]:
                    asyncio.run_coroutine_threadsafe(
                        self._bluetooth_stop_notify(client, char_uuid),
                        self.event_loop,
                    )
                    return True
        return False

    async def _bluetooth_scan(self, stop_event):
        async with BleakScanner(
            detection_callback=self._detection_callback,
        ):
            await stop_event.wait()

    def _detection_callback(
        self, device: BLEDevice, advertisement_data: AdvertisementData
    ):
        dev = BleDevice(
            name=advertisement_data.local_name,
            address=device.address,
            rssi=advertisement_data.rssi,
            uuids=advertisement_data.service_uuids,
            manufacturer_data=advertisement_data.manufacturer_data,
        )
        dev._device_hndl = device
        self.found_devices[device.address] = dev
        if self.on_device is not None:
            self.on_device(dev)

    async def _bluetooth_connect(
        self, device: BleDevice, disconnect_event: asyncio.Event
    ):
        async with BleakClient(
            device._device_hndl,
            self._disconnect_callback,
        ) as client:
            device._client = client
            self.connected_devices[client.address] = device
            self.status_devices[client.address] = BleStatus.Connected
            if client.address in self.on_connect:
                self.on_connect[client.address]()
            await disconnect_event.wait()
            del self.disconnect_events[client.address]

    def _disconnect_callback(self, client: BleakClient):
        if client.address in self.disconnect_events:
            self.disconnect_events[client.address].set()
        del self.connected_devices[client.address]
        del self.status_devices[client.address]
        if client.address in self.on_connect:
            del self.on_connect[client.address]
        if client.address in self.on_disconnect:
            self.on_disconnect[client.address]()
            del self.on_disconnect[client.address]

    async def _bluetooth_read(self, client: BleakClient, uuid: str):
        return await client.read_gatt_char(uuid)

    async def _bluetooth_write(
        self,
        client: BleakClient,
        uuid: str,
        data: bytes | bytearray,
        response: bool,
    ):
        return await client.write_gatt_char(uuid, data, response)

    async def _bluetooth_start_notify(
        self,
        client: BleakClient,
        uuid: str,
        on_data: Callable[[bytes | bytearray], None],
    ):
        await client.start_notify(uuid, lambda _, data: on_data(data))

    async def _bluetooth_stop_notify(self, client: BleakClient, uuid: str):
        await client.stop_notify(uuid)

    def _asyncloop(self):
        asyncio.set_event_loop(self.event_loop)
        self.event_loop.run_forever()
