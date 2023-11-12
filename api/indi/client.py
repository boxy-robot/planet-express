"""
Wraps the PyIndi library to make it easier to work with.
"""

import asyncio
import logging

import PyIndi


logger = logging.getLogger(__name__)


class BaseClient(PyIndi.BaseClient):
    def __init__(self):
        super().__init__()
        logger.debug('Creating an instance of IndiClient')

    def newDevice(self, d):
        '''Emmited when a new device is created from INDI server.'''
        logger.debug(f"New device {d.getDeviceName()}")

    def removeDevice(self, d):
        '''Emmited when a device is deleted from INDI server.'''
        logger.debug(f"Remove device {d.getDeviceName()}")

    def newProperty(self, p):
        '''Emmited when a new property is created for an INDI driver.'''
        logger.debug(f"New property {p.getName()} as {p.getTypeAsString()} for device {p.getDeviceName()}")

    def updateProperty(self, p):
        '''Emmited when a new property value arrives from INDI server.'''
        logger.debug(f"Update property {p.getName()} as {p.getTypeAsString()} for device {p.getDeviceName()}")

    def removeProperty(self, p):
        '''Emmited when a property is deleted for an INDI driver.'''
        logger.debug(f"Remove property {p.getName()} as {p.getTypeAsString()} for device {p.getDeviceName()}")

    def newMessage(self, d, m):
        '''Emmited when a new message arrives from INDI server.'''
        logger.debug(f"New Message {d.messageQueue(m)}")

    def serverConnected(self):
        '''Emmited when the server is connected.'''
        logger.debug(f"Server connected ({self.getHost()}:{self.getPort()})")

    def serverDisconnected(self, code):
        '''Emmited when the server gets disconnected.'''
        logger.debug(f"Server disconnected (exit code = {code},{self.getHost()}:{self.getPort()})")


def camel_case(s):
    parts = s.split("_")
    parts = parts[0:1] + list(map(str.title, parts[1:]))
    return "".join(parts)


POLL_INTERVAL = .1

async def poll(fn, *args, wait=True, poll_interval=POLL_INTERVAL, **kwargs):
    val = fn(*args, **kwargs)
    while not val:
        await asyncio.sleep(POLL_INTERVAL)
        val = fn(*args, **kwargs)

    return val


class ProxyObject:
    """Proxy undefined attrs to self.object."""
    def __getattr__(self, name):
        attr = getattr(self.object, camel_case(name))
        return attr

    def __repr__(self):
        return f"<{self.__class__.__name__}> " + self.__str__()


class Client(ProxyObject):
    def __init__(self, host, port=7624, poll_interval=0.2):
        self.host = host
        self.port = port
        self.poll_interval = poll_interval

        self.object = BaseClient()
        self.object.setServer(self.host, self.port)

    def connect(self):
        return self.object.connectServer()

    def disconnect(self):
        return self.object.disconnectServer()

    def get_devices(self):
        devices = self.object.getDevices()
        return [Device(d) for d in devices]

    async def get_device(self, name, wait=True):
        object = await poll(self.object.getDevice, name)
        return Device(object)

    async def get_text(self, name, wait=True):
        return await poll(self.object.getText, name)

    def set_blob_mode(self, *args, **kwargs):
        self.object.setBLOBMode(*args, **kwargs)


class Device(ProxyObject):
    def __init__(self, object):
        self.object = object

    @property
    def name(self):
        return self.object.getDeviceName()

    @property
    def is_connected(self):
        return self.object.isConnected()

    async def get_number(self, name, wait=True):
        return await self.get_property(name, wait=wait)

    async def get_switch(self, name, wait=True):
        return await self.get_property(name, wait=wait)

    async def get_text(self, name, wait=True):
        return await self.get_property(name, wait=wait)

    async def get_light(self, name, wait=True):
        return await self.get_property(name, wait=wait)

    async def get_blob(self, name, wait=True):
        return await self.get_property(name, wait=wait)

    def get_properties(self):
        props = self.object.getProperties()
        return [Property.factory(object) for object in props]

    async def get_property(self, name, wait=True):
        prop = await poll(self.object.getProperty, name)
        return Property.factory(prop)

    def __str__(self):
        return self.name

class Property(ProxyObject):
    object_type = None

    def __init__(self, object):
        self.object = self.object_type(object)

    @property
    def name(self):
        return self.object.getDeviceName()

    @property
    def type(self):
        return self.object.getType()

    @classmethod
    def factory(cls, object):
        MAPPING = {
            PyIndi.INDI_NUMBER: NumberProperty,
            PyIndi.INDI_SWITCH: SwitchProperty,
            PyIndi.INDI_TEXT: TextProperty,
            PyIndi.INDI_LIGHT: LightProperty,
            PyIndi.INDI_BLOB: BlobProperty,
        }

        cls = MAPPING[object.getType()]
        return cls(object)

    @property
    def widgets(self):
        return [Widget.factory(object) for object in self.object]

    def __getitem__(self, i):
        return Widget.factory(self.object[i])

    def __len__(self):
        return len(self.object)

    def __str__(self):
        return f"{self.name} {self.get_type_as_string()}"


class NumberProperty(Property):
    object_type = PyIndi.PropertyNumber


class SwitchProperty(Property):
    object_type = PyIndi.PropertySwitch

class TextProperty(Property):
    object_type = PyIndi.PropertyText


class LightProperty(Property):
    object_type = PyIndi.PropertyLight


class BlobProperty(Property):
    object_type = PyIndi.PropertyBlob

    @property
    def size(self):
        return self.object.getSize()

    @property
    def format(self):
        return self.object.getFormat()


class Widget(ProxyObject):
    def __init__(self, object):
        self.object = object

    @property
    def name(self):
        return self.object.getName()

    @property
    def label(self):
        return self.object.getLabel()

    @classmethod
    def factory(self, object):
        MAPPING = {
            PyIndi.WidgetViewNumber: NumberWidget,
            PyIndi.WidgetViewSwitch: SwitchWidget,
            PyIndi.WidgetViewText: TextWidget,
            PyIndi.WidgetViewLight: LightWidget,
            PyIndi.WidgetViewBlob: BlobWidget,
        }
        cls = MAPPING[type(object)]
        return cls(object)

    def __str__(self):
        return f"{self.name}({self.label})"


class TextWidget(Widget):
    def __str__(self):
        return super().__str__() + f" = {self.get_text()}"


class NumberWidget(Widget):
    def __str__(self):
         return super().__str__() + f"= {self.get_value()}"


class SwitchWidget(Widget):
    def __str__(self):
         return super().__str__() + f"= {self.get_state_as_string()}"


class LightWidget(Widget):
    def __str__(self):
         return super().__str__() + f" = {self.get_state_as_string()}"


class BlobWidget(Widget):
    def __str__(self):
         return super().__str__() + f" = <blob {self.get_size()} bytes>"
