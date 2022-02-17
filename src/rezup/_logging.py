
import sys
import logging
import warnings
from colorama import init, Fore

init(autoreset=True)


class ColorFormatter(logging.Formatter):
    Colors = {
        "DEBUG": Fore.BLUE,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA,
    }

    def format(self, record):
        color = self.Colors.get(record.levelname, "")
        return color + logging.Formatter.format(self, record)


def init_logging():
    formatter = ColorFormatter(
        fmt="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%X"
    )

    handler = logging.StreamHandler()
    handler.set_name("stream")
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    logger = logging.getLogger("rezup")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    logging.captureWarnings(True)
    warning = logging.getLogger("py.warnings")
    warning.addHandler(handler)

    if not sys.warnoptions:  # for prompting deprecation warning
        warnings.simplefilter("default")

    # hide source code line for shorter warning message
    def format_warn(message, category, *_, **__):
        return "%s:\n%s" % (category.__name__, message)
    warnings.formatwarning = format_warn


init_logging()
