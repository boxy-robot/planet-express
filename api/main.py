#!/usr/bin/python3
import asyncio
import logging
import sys

import api.app


async def main():
    return await api.app.main()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
