#!/usr/bin/python3

import logging
import sys
import time
import threading
from datetime import datetime, timezone

import PyIndi

from api.client import IndiClient


logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(message)s',
    datefmt='%H:%M:%S',
    level = logging.INFO
)


# Beware that ra/dec are in decimal hours/degrees
VEGA = (
    279.23473479 * 24.0 / 360.0,  # 18h 36m 56.33635s
    +38.78368896 # 38d 47' 01.2802"
)

ANDROMEDA = (
    10.68458333 * 24.0 / 360.0,  # 00h 42m 44.3s
    +41.26916667 # 41d 16' 9"
)


def main():
    client = IndiClient()
    client.setServer("indi", 7624)

    logger.info(f"Connecting to: {client.getHost()}:{client.getPort()}...")
    connect(client)

    logger.info("Listing devices...")
    list_devices(client)

    logger.info("Waiting for telescope...")
    telescope = telescope_connect(client)

    logger.info("Waiting for camera...")
    camera = camera_connect(client)

    logger.info("Goto Vega...")
    telescope_goto(client, telescope, VEGA)

    logger.info("Capture image of Vega...")
    exposure_times = [1.0, 5.0]
    capture_image(client, camera, exposure_times)

    logger.info("Goto Andromeda...")
    telescope_goto(client, telescope, ANDROMEDA)

    logger.info("Capture image of Andromeda...")
    exposure_times = [1.0, 5.0]
    capture_image(client, camera, exposure_times)

    logger.info("Disconnecting...")
    disconnect(client)
    return 0


def connect(client):
    # Connect to server
    if not client.connectServer():
        logger.error("Connection failed.")
        raise Exception("Connection failed.")

    # Waiting for device discovery
    time.sleep(1)
    logger.info("Connected.")


def disconnect(client):
    client.disconnectServer()


def list_devices(client):
    logger.info("Devices")
    devices = client.getDevices()
    for device in devices:
        logger.info(f"   > {device.getDeviceName()}")

    # Print all properties and their associated values.
    logger.info("List of Device Properties")
    for device in devices:
        logger.info(f"-- {device.getDeviceName()}")
        list_properties(device)


def list_properties(device):
    for prop in device.getProperties():
        logger.info(f"   > {prop.getName()} {prop.getTypeAsString()}")

        type = prop.getType()
        match type:
            case PyIndi.INDI_TEXT:
                for widget in PyIndi.PropertyText(prop):
                    logger.info(f"       {widget.getName()}({widget.getLabel()}) = {widget.getText()}")

            case PyIndi.INDI_NUMBER:
                for widget in PyIndi.PropertyNumber(prop):
                    logger.info(f"       {widget.getName()}({widget.getLabel()}) = {widget.getValue()}")

            case PyIndi.INDI_SWITCH:
                for widget in PyIndi.PropertySwitch(prop):
                    logger.info(f"       {widget.getName()}({widget.getLabel()}) = {widget.getStateAsString()}")

            case PyIndi.INDI_LIGHT:
                for widget in PyIndi.PropertyLight(prop):
                    logger.info(f"       {widget.getLabel()}({widget.getLabel()}) = {widget.getStateAsString()}")

            case PyIndi.INDI_BLOB:
                for widget in PyIndi.PropertyBlob(prop):
                    logger.info(f"       {widget.getName()}({widget.getLabel()}) = <blob {widget.getSize()} bytes>")


def telescope_connect(client):
    telescope = client.getDevice("Telescope Simulator")
    while not telescope:
        time.sleep(1)
        telescope = client.getDevice("Telescope Simulator")

    telescope_con = telescope.getSwitch("CONNECTION")
    while not telescope_con:
        time.sleep(1)
        telescope_con = telescope.getSwitch("CONNECTION")

    if not telescope.isConnected():
        telescope_con.reset()
        telescope_con[0].setState(PyIndi.ISS_ON)
        client.sendNewProperty(telescope_con)

    return telescope


def telescope_goto(client, telescope, destination):
    ra, dec = destination
    logger.info(f"Moving: {telescope.getDeviceName()} to RA: {ra} DEC: {dec}")

    # We want to set the ON_COORD_SET switch to engage tracking after goto
    # device.getSwitch is a helper to retrieve a property vector
    switch = telescope.getSwitch("ON_COORD_SET")
    while not switch:
        time.sleep(0.5)
        switch = telescope.getSwitch("ON_COORD_SET")

    # the order below is defined in the property vector, look at the standard Properties page
    # or enumerate them in the Python shell when you're developing your program
    switch.reset()
    switch[0].setState(PyIndi.ISS_ON)  # index 0-TRACK, 1-SLEW, 2-SYNC
    client.sendNewProperty(switch)

    # We set the desired coordinates
    coords = telescope.getNumber("EQUATORIAL_EOD_COORD")
    while not coords:
        time.sleep(1)
        coords = telescope.getNumber("EQUATORIAL_EOD_COORD")

    # Send them
    coords[0].setValue(ra)
    coords[1].setValue(dec)
    client.sendNewProperty(coords)

    # Wait for slew
    while coords.getState() == PyIndi.IPS_BUSY:
        logger.info(f"Scope Moving {coords[0].value}, {coords[1].value}")
        time.sleep(1)


def camera_connect(client):
    camera = client.getDevice("CCD Simulator")
    while not camera:
        time.sleep(1)
        camera = client.getDevice("CCD Simulator")

    camera_con = camera.getSwitch("CONNECTION")
    while not (camera_con):
        time.sleep(1)
        camera_con = camera.getSwitch("CONNECTION")

    if not camera.isConnected():
        camera_con.reset()
        camera_con[0].setState(PyIndi.ISS_ON)  # the "CONNECT" switch
        client.sendNewProperty(camera_con)

    # Ensure the CCD simulator snoops the telescope simulator
    # otherwise you may not have a picture of vega
    active_devices = camera.getText("ACTIVE_DEVICES")
    while not active_devices:
        time.sleep(1)
        active_devices = camera.getText("ACTIVE_DEVICES")

    active_devices[0].setText("Telescope Simulator")
    client.sendNewProperty(active_devices)

    return camera


def capture_image(client, camera, exposure_times):
    # Inform the indi server that we want to receive the "CCD1" blob
    client.setBLOBMode(PyIndi.B_ALSO, camera.getDeviceName(), "CCD1")

    ccd1 = camera.getBLOB("CCD1")
    while not ccd1:
        time.sleep(1)
        ccd1 = camera.getBLOB("CCD1")

    exposure = camera.getNumber("CCD_EXPOSURE")
    while not exposure:
        time.sleep(1)
        exposure = camera.getNumber("CCD_EXPOSURE")


    # We define an event for newBlob event
    for i, exposure_time in enumerate(exposure_times):
        exposure[0].setValue(exposure_time)
        client.sendNewProperty(exposure)
        time.sleep(exposure_time + 1)

        # Process the received blob
        for blob in ccd1:
            logger.info(f"Blob received. name: {blob.getName()} size: {blob.getSize()} format: {blob.getFormat()}")
            data = blob.getblobdata()  # bytearray

            now = datetime.now(timezone.utc)
            formatted_date = now.strftime("%Y-%m-%dT%H-%M-%S-%f")[:-3] + "Z"
            with open(f"/app/data/{formatted_date}.fits", "wb") as f:
                f.write(data)

if __name__ == "__main__":
    sys.exit(main())
