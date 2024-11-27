#!/usr/bin/env python3
"""
NullSMTPD module that allows to run a mock email server that just logs all incoming emails to a file
instead of actually trying to send them. Helps for developing applications that utilize email,
without spamming customers' emails and not having overhead from some GUI program.
"""
import argparse
import asyncio
import os
import time

from aiosmtpd.controller import Controller

from .logger import configure_logging
from .version import __version__

NULLSMTPD_DIRECTORY = os.path.join(os.path.expanduser("~"), ".nullsmtpd")


# pylint: disable=too-few-public-methods
class NullSMTPDHandler:
    def __init__(self, logger, mail_dir, output_messages=True, file_extension="eml"):
        """
        :param logger: Logger to use for the handler
        :param mail_dir: Directory to write emails to
        :param output_messages: Boolean flag on whether to output messages to the logger
        :param file_extension: File extension to use for saved emails
        """
        self.logger = logger
        if mail_dir is None or not isinstance(mail_dir, str):
            msg = "Invalid mail_dir variable: {}".format(mail_dir)
            self.logger.error(msg)
            raise SystemExit(msg)
        if not os.path.isdir(mail_dir):
            try:
                os.mkdir(mail_dir)
            except IOError as io_error:
                self.logger.error(str(io_error))
                raise
        self.mail_dir = mail_dir
        self.print_messages = output_messages is True
        self.file_extension = file_extension.lstrip(".")  # Ensure no leading dot
        self.logger.info("Mail Directory: {:s}".format(mail_dir))
        self.logger.info("File Extension: .{:s}".format(self.file_extension))

    async def handle_DATA(self, _, __, envelope):
        """
        Process incoming email messages as they're received by the server.
        """
        mail_from = envelope.mail_from
        rcpt_tos = envelope.rcpt_tos
        data = envelope.content.decode('utf-8')

        self.logger.info("Incoming mail from {:s}".format(mail_from))
        for recipient in rcpt_tos:
            self.logger.info("Mail received for {:s}".format(recipient))
            mail_file = "{:d}.{:s}.{:s}".format(int(time.time()), mail_from, self.file_extension)
            mail_path = os.path.join(self.mail_dir, recipient, mail_file)
            if not os.path.isdir(os.path.join(self.mail_dir, recipient)):
                os.mkdir(os.path.join(self.mail_dir, recipient))
            with open(mail_path, 'a') as open_file:
                open_file.write(data + "\n")

            if self.print_messages:
                self.logger.info(data)
        return '250 OK'



def _parse_args():
    """
    Parse the CLI arguments for use by NullSMTPD.

    :return: namespace containing the arguments parsed from the CLI
    """
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--no-fork",
        action="store_true",
        help=(
            "Don't fork and run nullsmtpd as a daemon. "
            "Additionally, this will print all log messages to stdout/stderr "
            "and all emails to stdout."
        )
    )
    parser.add_argument(
        "-H",
        "--host",
        type=str,
        default="localhost",
        help="Host to listen on (defaults to localhost)"
    )
    parser.add_argument(
        "-P",
        "--port",
        type=int,
        default=25,
        help="Port to listen on (defaults to 25)"
    )
    parser.add_argument(
        "--mail-dir",
        type=str,
        default=NULLSMTPD_DIRECTORY,
        help="Location to write logs and emails (defaults to ~/.nullsmtpd)"
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s (" + __version__ + ")"
    )
    parser.add_argument(
        "-fx",
        "--file-extension",
        type=str,
        default="eml",
        help="File extension for saved emails (default: 'eml')"
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    if not os.path.isdir(args.mail_dir):
        os.mkdir(args.mail_dir)

    if args.no_fork is not True:
        pid = os.fork()
        if pid != 0:
            raise SystemExit("Could not fork nullsmtpd")

    host = args.host
    port = args.port
    output_messages = 'no_fork' in args and args.no_fork
    logger = configure_logging(args.mail_dir, output_messages)
    mail_dir = args.mail_dir
    file_extension = args.file_extension

    logger.info(
        "Starting nullsmtpd {:s} on {:s}:{:d}".format(
            __version__,
            host,
            port
        )
    )
    loop = asyncio.get_event_loop()
    nullsmtpd = NullSMTPDHandler(logger, mail_dir, output_messages, file_extension)
    controller = Controller(nullsmtpd, hostname=host, port=port)
    controller.start()

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info('Stopping nullsmtpd')
        controller.stop()
        loop.stop()



if __name__ == "__main__":
    main()
