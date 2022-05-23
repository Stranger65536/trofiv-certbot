# coding=utf-8
"""
Utilities
"""
from logging import getLogger, WARNING, INFO, StreamHandler, \
    Formatter, Handler
from subprocess import PIPE, STDOUT, TimeoutExpired
from typing import List, Tuple, Union
from warnings import filterwarnings

# noinspection PyPackageRequirements
# noinspection PyPackageRequirements
from command_runner import command_runner


def default_handler() -> Handler:
    """
    Returns default configured console handler
    """
    console_handler = StreamHandler()
    console_handler.setLevel(INFO)
    formatter = Formatter("[%(asctime)s] %(levelname)s %(name)s "
                          "%(threadName)s "
                          "{%(pathname)s:%(lineno)d} "
                          " - %(message)s")
    console_handler.setFormatter(formatter)
    return console_handler


def configure_logger() -> None:
    """
    Configures default logger
    """
    console = default_handler()
    getLogger().addHandler(console)
    getLogger("").addHandler(console)
    getLogger("").setLevel(INFO)
    getLogger().addHandler(console)
    getLogger().setLevel(INFO)
    getLogger("requests").setLevel(WARNING)
    getLogger("urllib3").setLevel(WARNING)
    getLogger("engineio.server").setLevel(WARNING)
    getLogger("socketio.server").setLevel(WARNING)
    getLogger("werkzeug").setLevel(WARNING)
    filterwarnings("ignore", module="urllib3")


def run_subprocess(
    command: Union[str, List[str]],
    timeout: int,
    *popenargs,
    **kwargs,
) -> Tuple[int, str]:
    """
    Runs subprocess with real time output. Returns exit code
    """
    kwargs["stdout"] = PIPE
    kwargs["stderr"] = STDOUT
    kwargs["universal_newlines"] = True
    code, out = command_runner(
        command,
        *popenargs,
        live_output=True,
        **kwargs,
        timeout=timeout,
    )
    if code == -254:
        raise TimeoutExpired(command, timeout, out)

    return code, out
