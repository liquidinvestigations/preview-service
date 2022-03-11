# BUFFER CLONED FROM:
# https://github.com/encode/uvicorn/blob/0.14.0/uvicorn/workers.py
# ==================================
import asyncio
import logging
import signal
from typing import Any

from gunicorn.workers.base import Worker

from uvicorn.config import Config
from uvicorn.main import Server


class UvicornWorker(Worker):
    """
    A worker class for Gunicorn that interfaces with an ASGI consumer callable,
    rather than a WSGI callable.
    """

    CONFIG_KWARGS = {"loop": "auto", "http": "auto"}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(UvicornWorker, self).__init__(*args, **kwargs)

        self._server = None

        logger = logging.getLogger("uvicorn.error")
        logger.handlers = self.log.error_log.handlers
        logger.setLevel(self.log.error_log.level)
        logger.propagate = False

        logger = logging.getLogger("uvicorn.access")
        logger.handlers = self.log.access_log.handlers
        logger.setLevel(self.log.access_log.level)
        logger.propagate = False

        config_kwargs = {
            "app": None,
            "log_config": None,
            "timeout_keep_alive": self.cfg.keepalive,

            # ====================================================
            # EDITED HERE FOR LIQUID INVESTIGATIONS:
            # `self.timeout` --> `self.cfg.timeout` as mentioned here:
            # https://github.com/encode/uvicorn/issues/611#issuecomment-609906638
            "timeout_notify": self.cfg.timeout,
            # ====================================================

            "callback_notify": self.callback_notify,
            "limit_max_requests": self.max_requests,
            "forwarded_allow_ips": self.cfg.forwarded_allow_ips,
        }

        if self.cfg.is_ssl:
            ssl_kwargs = {
                "ssl_keyfile": self.cfg.ssl_options.get("keyfile"),
                "ssl_certfile": self.cfg.ssl_options.get("certfile"),
                "ssl_keyfile_password": self.cfg.ssl_options.get("password"),
                "ssl_version": self.cfg.ssl_options.get("ssl_version"),
                "ssl_cert_reqs": self.cfg.ssl_options.get("cert_reqs"),
                "ssl_ca_certs": self.cfg.ssl_options.get("ca_certs"),
                "ssl_ciphers": self.cfg.ssl_options.get("ciphers"),
            }
            config_kwargs.update(ssl_kwargs)

        if self.cfg.settings["backlog"].value:
            config_kwargs["backlog"] = self.cfg.settings["backlog"].value

        config_kwargs.update(self.CONFIG_KWARGS)

        self.config = Config(**config_kwargs)

    def init_process(self) -> None:
        self.config.setup_event_loop()
        super(UvicornWorker, self).init_process()

    def init_signals(self) -> None:
        # Reset signals so Gunicorn doesn't swallow subprocess return codes
        # other signals are set up by Server.install_signal_handlers()
        # See: https://github.com/encode/uvicorn/issues/894
        for s in self.SIGNALS:
            signal.signal(s, signal.SIG_DFL)

    def run(self) -> None:
        self.config.app = self.wsgi
        server = Server(config=self.config)
        self._server = server
        loop = asyncio.get_event_loop()
        loop.run_until_complete(server.serve(sockets=self.sockets))

    async def callback_notify(self) -> None:
        self.notify()


class UvicornH11Worker(UvicornWorker):
    CONFIG_KWARGS = {"loop": "asyncio", "http": "h11"}


# ADDED HERE FOR LIQUID INVESTIGATIONS
# uvicorn worker doesn't listen to the gunicorn timeout; fix is this class:
# https://github.com/encode/uvicorn/issues/611#issuecomment-806508259
# =================================
class RequestKillerWorker(UvicornWorker):
    def notify(self):
        if not self._server.server_state.tasks:
            self.tmp.notify()
