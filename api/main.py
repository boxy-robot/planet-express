#!/usr/bin/python3

import logging
import sys
import time

import PyIndi

from api.client import IndiClient


logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(message)s',
    level = logging.INFO
)


def main():
    client = IndiClient()
    client.setServer("indi", 7624)

    # Connect to server
    logger.info(f"Connecting to: {client.getHost()}:{client.getPort()}...")
    if not client.connectServer():
        logger.error(f"Connection failed.")
        return 1

    # Waiting for device discovery
    time.sleep(1)

    logger.info("Devices")
    devices = client.getDevices()
    for device in devices:
        logger.info(f"   > {device.getDeviceName()}")

    # Print all properties and their associated values.
    logger.info("List of Device Properties")
    for device in devices:
        logger.info(f"-- {device.getDeviceName()}")
        genericPropertyList = device.getProperties()

        for genericProperty in genericPropertyList:
            logger.info(f"   > {genericProperty.getName()} {genericProperty.getTypeAsString()}")

            if genericProperty.getType() == PyIndi.INDI_TEXT:
                for widget in PyIndi.PropertyText(genericProperty):
                    logger.info(f"       {widget.getName()}({widget.getLabel()}) = {widget.getText()}")

            if genericProperty.getType() == PyIndi.INDI_NUMBER:
                for widget in PyIndi.PropertyNumber(genericProperty):
                    logger.info(f"       {widget.getName()}({widget.getLabel()}) = {widget.getValue()}")

            if genericProperty.getType() == PyIndi.INDI_SWITCH:
                for widget in PyIndi.PropertySwitch(genericProperty):
                    logger.info(f"       {widget.getName()}({widget.getLabel()}) = {widget.getStateAsString()}")

            if genericProperty.getType() == PyIndi.INDI_LIGHT:
                for widget in PyIndi.PropertyLight(genericProperty):
                    logger.info(f"       {widget.getLabel()}({widget.getLabel()}) = {widget.getStateAsString()}")

            if genericProperty.getType() == PyIndi.INDI_BLOB:
                for widget in PyIndi.PropertyBlob(genericProperty):
                    logger.info(f"       {widget.getName()}({widget.getLabel()}) = <blob {widget.getSize()} bytes>")

    # Disconnect from the indiserver
    logger.info("Disconnecting...")
    client.disconnectServer()
    return 0


if __name__ == "__main__":
    sys.exit(main())
