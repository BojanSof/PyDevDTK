import asyncio
import enum
import threading
from typing import Callable

from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData


class BleStatus(enum.Enum):
    Disconnected = enum.auto()
    Connecting = enum.auto()
    Connected = enum.auto()
    Disconnecting = enum.auto()
    WriteSuccessful = enum.auto()
    NotificationsEnabled = enum.auto()
    NotificationsDisabled = enum.auto()


class BleDevice:
    def __init__(
        self,
        name: str | None,
        address: str,
        rssi: int,
        uuids: list[str],
        manufacturer_data: dict[int, bytes],
        device_hndl: BLEDevice,
        client: BleakClient | None = None,
    ):
        self.name = name
        self.address = address
        self.rssi = rssi
        self.uuids = uuids
        self.manufacturer_data = manufacturer_data
        self._device_hndl = device_hndl
        self._client = client

    def __str__(self) -> str:
        return self.name if self.name is not None else ""


class Ble:
    def __init__(self):
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
        self.found_devices = {}  # clear previously found devices
        self.on_device = on_device
        self.scan_stop_event.clear()
        asyncio.run_coroutine_threadsafe(
            self.bluetooth_scan(self.scan_stop_event), self.event_loop
        )
        self.scanning = True

    def stop_scan(self):
        if self.scanning:
            self.event_loop.call_soon_threadsafe(self.scan_stop_event.set)
            self.scanning = False

    def is_scanning(self) -> bool:
        return self.scanning

    def get_found_devices(self) -> list[BleDevice]:
        return list(self.found_devices.values())

    def connect(
        self,
        dev: BleDevice,
        on_connect: Callable[[], None] | None = None,
        on_disconnect: Callable[[], None] | None = None,
    ):
        if not self.is_connected(dev):
            if on_connect is not None:
                self.on_connect[dev.address] = on_connect
            if on_disconnect is not None:
                self.on_disconnect[dev.address] = on_disconnect
            self.disconnect_events[dev.address] = asyncio.Event()
            self.status_devices[dev.address] = BleStatus.Connecting
            asyncio.run_coroutine_threadsafe(
                self.bluetooth_connect(
                    dev, self.disconnect_events[dev.address]
                ),
                self.event_loop,
            )

    def disconnect(self, dev: BleDevice):
        if self.is_connected(dev):
            self.status_devices[dev.address] = BleStatus.Disconnecting
            self.event_loop.call_soon_threadsafe(
                self.disconnect_events[dev.address].set
            )

    def is_connected(self, dev: BleDevice) -> bool:
        return dev.address in self.connected_devices

    def get_connected_devices(self) -> list[BleDevice]:
        return list(self.connected_devices.values())

    def get_status(self, dev: BleDevice) -> BleStatus | None:
        if dev.address in self.status_devices:
            return self.status_devices[dev.address]
        else:
            return None

    def get_services_and_characteristics(self, dev: BleDevice) -> dict:
        if not self.is_connected(dev):
            services_collection = None
        else:
            services_collection = {}
            client = self.connected_devices[dev.address]._client
            for _, service in client.services.services.items():
                services_collection[service.uuid] = {
                    "name": service.description,
                    "service": service,
                }
                service_characteristics = {}
                for characteristic in service.characteristics:
                    service_characteristics[characteristic.uuid] = {
                        "name": characteristic.description,
                        "properties": characteristic.properties,
                        "characteristic": characteristic,
                    }
                    characteristic_descriptors = {}
                    for descriptor in characteristic.descriptors:
                        characteristic_descriptors[descriptor.uuid] = {
                            "name": descriptor.description,
                            "descriptor": descriptor,
                        }
                    service_characteristics[characteristic.uuid][
                        "descriptors"
                    ] = characteristic_descriptors
                services_collection[service.uuid][
                    "characteristics"
                ] = service_characteristics
        return services_collection

    def read_characteristic(
        self, dev: BleDevice, char_uuid: str
    ) -> bytearray | None:
        if self.is_connected(dev):
            client = self.connected_devices[dev.address]._client
            chars = list(client.services.characteristics.values())
            chars_uuids = [char.uuid for char in chars]
            chars_properties = [char.properties for char in chars]
            if char_uuid in chars_uuids:
                i_char = chars_uuids.index(char_uuid)
                if "read" in chars_properties[i_char]:
                    future = asyncio.run_coroutine_threadsafe(
                        self.bluetooth_read(client, char_uuid), self.event_loop
                    )
                    return future.result()
        return None

    def write_characteristic(
        self,
        dev: BleDevice,
        char_uuid: str,
        data: bytes | bytearray,
        response: bool,
    ):
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
                        self.bluetooth_write(
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
        if self.is_connected(dev):
            client = self.connected_devices[dev.address]._client
            chars = list(client.services.characteristics.values())
            chars_uuids = [char.uuid for char in chars]
            chars_properties = [char.properties for char in chars]
            if char_uuid in chars_uuids:
                i_char = chars_uuids.index(char_uuid)
                if "notify" in chars_properties[i_char]:
                    asyncio.run_coroutine_threadsafe(
                        self.bluetooth_start_notify(
                            client, char_uuid, on_data
                        ),
                        self.event_loop,
                    )
                    return True
        return False

    def stop_notifications(self, dev: BleDevice, char_uuid: str) -> bool:
        if self.is_connected(dev):
            client = self.connected_devices[dev.address]._client
            chars = list(client.services.characteristics.values())
            chars_uuids = [char.uuid for char in chars]
            chars_properties = [char.properties for char in chars]
            if char_uuid in chars_uuids:
                i_char = chars_uuids.index(char_uuid)
                if "notify" in chars_properties[i_char]:
                    asyncio.run_coroutine_threadsafe(
                        self.bluetooth_stop_notify(client, char_uuid),
                        self.event_loop,
                    )
                    return True
        return False

    async def bluetooth_scan(self, stop_event):
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
            device_hndl=device,
        )
        self.found_devices[device.address] = dev
        if self.on_device is not None:
            self.on_device(dev)

    async def bluetooth_connect(
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

    async def bluetooth_read(self, client: BleakClient, uuid: str):
        return await client.read_gatt_char(uuid)

    async def bluetooth_write(
        self,
        client: BleakClient,
        uuid: str,
        data: bytes | bytearray,
        response: bool,
    ):
        return await client.write_gatt_char(uuid, data, response)

    async def bluetooth_start_notify(
        self,
        client: BleakClient,
        uuid: str,
        on_data: Callable[[bytes | bytearray], None],
    ):
        await client.start_notify(uuid, lambda _, data: on_data(data))

    async def bluetooth_stop_notify(self, client: BleakClient, uuid: str):
        await client.stop_notify(uuid)

    def _asyncloop(self):
        asyncio.set_event_loop(self.event_loop)
        self.event_loop.run_forever()
