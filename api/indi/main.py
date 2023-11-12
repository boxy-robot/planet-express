#!/usr/bin/python3
import asyncio
import logging
import sys
import time
import threading
from datetime import datetime, timezone

import PyIndi

from indi.client import Client
import api.app


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


async def main():
    client = Client("indi", 7624)

    logger.info(f"Connecting to: {client.host}:{client.port}...")
    connect(client)

    logger.info("Listing devices...")
    await asyncio.sleep(1)  # Wait for device discovery
    list_devices(client)

    logger.info("Waiting for telescope...")
    telescope = await telescope_connect(client, "Telescope Simulator")

    logger.info("Waiting for camera...")
    camera = await camera_connect(client, "CCD Simulator")

    logger.info("Track Vega...")
    await telescope_track(client, telescope, VEGA)

    logger.info("Capture image of Vega...")
    exposure_times = [1.0, 5.0]
    await capture_image(client, camera, exposure_times)

    logger.info("Track Andromeda...")
    await telescope_track(client, telescope, ANDROMEDA)

    logger.info("Capture image of Andromeda...")
    exposure_times = [1.0, 5.0]
    await capture_image(client, camera, exposure_times)

    logger.info("Disconnecting...")
    disconnect(client)
    return 0


def connect(client):
    # Connect to server
    if not client.connect():
        logger.error("Connection failed.")
        raise Exception("Connection failed.")


def disconnect(client):
    client.disconnect()


def list_devices(client):
    logger.info("Devices")
    devices = client.get_devices()
    for device in devices:
        logger.info(f"   > {device.name}")

    # Print all properties and their associated values.
    logger.info("List of Device Properties")
    for device in devices:
        logger.info(f"-- {device}")
        for prop in device.get_properties():
            logger.info(f"   > {prop}")
            for widget in prop.widgets:
                logger.info(f"       {widget}")


async def telescope_connect(client, name):
    telescope = await client.get_device(name)
    con = await telescope.get_switch("CONNECTION")

    if not telescope.is_connected:
        con.reset()
        con[0].set_state(PyIndi.ISS_ON)
        client.send_new_property(con)

    return telescope


async def telescope_track(client, telescope, destination):
    ra, dec = destination
    logger.info(f"Moving {telescope.name} to RA: {ra} DEC: {dec}")

    # We want to set the ON_COORD_SET switch to engage tracking after goto
    # device.getSwitch is a helper to retrieve a property vector
    switch = await telescope.get_switch("ON_COORD_SET")

    # the order below is defined in the property vector, look at the standard Properties page
    # or enumerate them in the Python shell when you're developing your program
    switch.reset()
    switch[0].set_state(PyIndi.ISS_ON)  # index 0-TRACK, 1-SLEW, 2-SYNC
    client.send_new_property(switch)

    # We set the desired coordinates
    coords = await telescope.get_number("EQUATORIAL_EOD_COORD")

    # Send them
    coords[0].set_value(ra)
    coords[1].set_value(dec)
    client.send_new_property(coords)

    # Wait for slew
    while coords.get_state() == PyIndi.IPS_BUSY:
        logger.info(f"Scope Moving {coords[0].value}, {coords[1].value}")
        time.sleep(1)


async def camera_connect(client, name):
    camera = await client.get_device(name)
    con = await camera.get_switch("CONNECTION")

    if not camera.is_connected:
        con.reset()
        con[0].set_state(PyIndi.ISS_ON)  # the "CONNECT" switch
        client.send_new_property(camera_con)

    # Ensure the CCD simulator snoops the telescope simulator
    active_devices = await camera.get_text("ACTIVE_DEVICES")
    active_devices[0].set_text("Telescope Simulator")
    client.send_new_property(active_devices)
    return camera


async def capture_image(client, camera, exposure_times):
    # Inform the indi server that we want to receive the "CCD1" blob
    client.set_blob_mode(PyIndi.B_ALSO, camera.name, "CCD1")
    ccd1 = await camera.get_blob("CCD1")
    exposure = await camera.get_number("CCD_EXPOSURE")

    for i, exposure_time in enumerate(exposure_times):
        exposure[0].set_value(exposure_time)
        client.send_new_property(exposure)
        time.sleep(exposure_time + 1)

        for blob in ccd1:
            logger.info(f"Blob received. name: {blob.name} size: {blob.size} format: {blob.format}")
            data = blob.getblobdata()  # bytearray

            now = datetime.now(timezone.utc)
            formatted_date = now.strftime("%Y-%m-%dT%H-%M-%S-%f")[:-3] + "Z"
            with open(f"/app/data/{formatted_date}.fits", "wb") as f:
                f.write(data)

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
