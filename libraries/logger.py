import datetime
import logging
import time

from colorama import Fore

logging.getLogger('filelock').propagate = False
logging.basicConfig(
    # filename='logger.log',
    level=logging.INFO,
    format='%(message)s'
)


class Logger:
    def __init__(
            self, logger_name='Unknown',
            classic=False,
            normal=False
    ):

        self.logger_name = logger_name
        self.classic = classic
        self.normal = normal
        self.last_log = None

        self.logger = logging.getLogger('Logger')

    @staticmethod
    def sleep(timeout):
        time.sleep(timeout)

    def log(self, message, status, *args, **kwargs):

        # Printing Exceptions Error
        if not str(message) and isinstance(message, object) and not isinstance(message, str):
            attr = str(type(message).__name__)
        else:
            attr = ''

        message = str(message) + attr

        if status == 'info':
            status_color = Fore.WHITE
        elif status == 'status':
            status_color = Fore.LIGHTYELLOW_EX
        elif status == 'warning':
            status_color = Fore.YELLOW
        elif status == 'success':
            status_color = Fore.BLUE
        elif status == 'error':
            status_color = Fore.RED
        elif status == 'debug':
            status_color = Fore.GREEN
        elif status == 'checkout':
            status_color = Fore.LIGHTBLUE_EX
        else:
            status_color = Fore.CYAN

        # MODE 1
        if self.classic:
            if status in ['error', 'warning', 'debug']:
                mess = f'[{status.upper()}]:{status_color} {message}{Fore.RESET}'
            else:
                mess = f'{status_color} {message}{Fore.RESET}'

        # MODE 2
        elif self.normal:
            mess = f'[{datetime.datetime.now().strftime("%H:%M:%S")}][{status.upper()}]:' \
                   f'{status_color} {message}{Fore.RESET}'

        else:
            if kwargs.get('retry'):
                if isinstance(kwargs['retry'], float) or isinstance(kwargs['retry'], int):
                    retry = kwargs['retry']
                    message = message + f' Retry in {retry} sec...'
                    # Sleeping
                    self.sleep(timeout=retry)
                else:
                    message = message + f' Retry...'

            logger_ = f'{self.logger_name}'
            mess = f'[{datetime.datetime.now().strftime("%H:%M:%S.%f")}]' \
                   f'[{status.upper()}]{status_color}[{logger_}] => {message}{Fore.RESET}'

        self.logger.info(mess)

    def error(self, message, *args, **kwargs):
        self.log(message, 'error', *args, **kwargs)

    def info(self, message, *args, **kwargs):
        self.log(message, 'info', *args, **kwargs)

    def status(self, message, **kwargs):
        self.log(message, 'status', **kwargs)

    def success(self, message, *args, **kwargs):
        self.log(message, 'success', *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        self.log(message, 'warning', *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        self.log(message, 'debug', *args, **kwargs)


logger = Logger(classic=True, logger_name='Default-Logger')
