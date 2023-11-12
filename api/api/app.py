import asyncio
import collections
import logging
import os.path

import tornado
import tornado.log

import indi


class HealthHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("OK\n")


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("templates/index.html", **self.get_context())

    def get_context(self):
        return {
            "indi_client": self.application.indi_client,
            "devices": self.application.indi_client.get_devices()
        }

class DeviceHandler(tornado.web.RequestHandler):
    async def get(self, device_name):
        device = await self.application.indi_client.get_device(device_name)
        context = self.get_context()
        context.update({
            "device": device,
            "groups": self.get_groups(device),
        })
        self.render("templates/device.html", **context)

    def get_groups(self, device):
        props = device.get_properties()
        groups = collections.defaultdict(list)
        for prop in props:
            groups[prop.get_group_name()].append(prop)

        return groups

    def get_context(self):
        return {
            "device": None,
        }

class Application(tornado.web.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.indi_client = indi.Client("indi", 7624)

    async def startup(self):
        logging.info("Connecting INDI client...")
        if not self.indi_client.connect():
            logging.error("INDI client connection failed")

    def shutdown(self):
        self.indi_client.disconnect()


def make_app():
    app = Application([
            (r"/", IndexHandler),
            (r"/devices/([a-zA-Z0-9%]+)", DeviceHandler),
            (r"/health", HealthHandler),
            # (r"/static", tornado.web.StaticFileHandler),

        ],
        static_path=os.path.join(os.path.dirname(__file__), "templates/static"),
        debug=True,
    )
    return app

async def main():
    tornado.log.enable_pretty_logging()

    logging.info("Starting server at http://localhost:8888")
    app = make_app()
    await app.startup()
    app.listen(8888)
    shutdown_event = asyncio.Event()
    await shutdown_event.wait()
    app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
