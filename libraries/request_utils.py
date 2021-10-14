import ssl
import time
from collections import OrderedDict
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from requests import Session
from requests import exceptions
from requests.adapters import HTTPAdapter
from urllib3.exceptions import HTTPError
from urllib3.poolmanager import PoolManager
from urllib3.util.retry import Retry

from libraries.logger import Logger


class CancelledRequest(Exception):
    pass


class MaxRequestsExceed(Exception):
    pass


class SessionAdapter(HTTPAdapter):
    def __init__(self, pool_connections=10,
                 pool_maxsize=10, max_retries=0,
                 pool_block=False):
        if max_retries == 0:
            self.max_retries = Retry(0, read=False)
        else:
            self.max_retries = Retry.from_int(max_retries)
        self.config = {}
        self.proxy_manager = {}

        super(HTTPAdapter, self).__init__()

        self._pool_connections = pool_connections
        self._pool_maxsize = pool_maxsize
        self._pool_block = pool_block
        self.poolmanager = None
        self.init_poolmanager(pool_connections, pool_maxsize, block=pool_block)

    def init_poolmanager(self, connections, maxsize, block=None, **pool_kwargs):
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_TLSv1_2
        )


class PowerSession(Session):
    def __init__(self, log=None, error_delay=5.0, session_name='Session'):
        super(PowerSession, self).__init__()

        self.parser = 'html.parser'
        self.hooks['response'] = [self.response_hook]

        self.sessions_log = []
        self.last_response = False
        self.timer = {'start': 0.0, 'end': 0.0}
        self.error_delay = error_delay

        self.retry_log = f' Retrying in {self.error_delay} seconds' if self.error_delay != 0.0 else ''
        self.log = log if log and isinstance(log, Logger) else Logger(session_name)

        self.mount(
            'https://',
            SessionAdapter()
        )
        # self.trust_env = False

    def check_tls_version(self):
        return self.get('https://www.howsmyssl.com/a/check').json().get('tls_version')

    def response_hook(self, response, *args, **kwargs):
        self.timer['end'] = time.time()

        request = response.request
        url = urlparse(request.url)
        response.connection_time = self.timer['end'] - self.timer['start']

        response.soup = self.soupize(response.text) if response.text else None

        response.domain = f'{url.scheme}://{url.hostname}'

        self.last_response = response
        self.sessions_log.append({
            'url': str(request.url),
            'code': response.status_code,
            'time': time.ctime(),
            'connection_time': response.connection_time
        })
        return response

    def request(self, method, url, *args, **kwargs):
        count = 0
        self.timer['start'] = time.time()
        kwargs.setdefault('allow_redirects', True)

        if kwargs.get('headers'):  # order headers every time
            kwargs['headers'] = OrderedDict(kwargs['headers'])

        if not kwargs.get('timeout'):  # set timeout default = 10
            kwargs['timeout'] = 10

        if kwargs.pop('no_cache', False):
            no_cache = str(time.time()).replace('.', '')
            if kwargs.get('params'):
                kwargs['params'].update({'_': no_cache})
            else:
                kwargs['params'] = {'_': no_cache}

        while 1:
            try:
                response = self.make_request(method=method, url=url, *args, **kwargs)

                if kwargs.get('allowed_codes') and response.status_code not in kwargs['allowed_codes']:
                    self.log.error(f'Bad Response: {response}')
                return response

            except exceptions.ConnectTimeout:
                error = exceptions.ConnectTimeout
                self.log.error(f'Request timed out.{self.retry_log}')

            except exceptions.ConnectionError:
                error = exceptions.ConnectionError
                self.log.error(f'Connection error.{self.retry_log}')

            except exceptions.HTTPError:
                error = exceptions.HTTPError
                self.log.error(f'Request HTTP error.{self.retry_log}')

            except exceptions.ReadTimeout:
                error = exceptions.ReadTimeout
                self.log.error(f'Request read timed out.{self.retry_log}')

            except exceptions.Timeout:
                error = exceptions.Timeout
                self.log.error(f'Request timed out.{self.retry_log}')
                self.log.debug(f"{str(type(error))}: {str(error)}")

            except (exceptions.RequestException, HTTPError) as error:
                if 'no schema supplied' in str(error).lower():
                    self.log.error('Bad Error. Closing...')
                    raise CancelledRequest
                self.log.error(f'Bad Error: {error}.{self.retry_log}')

            except Exception as error:
                if str(type(error).__name__) == 'CancelledRequest' or str(error) == 'CancelledRequest':
                    raise CancelledRequest

                self.log.error(error, retry=self.retry_log)

            self.last_response = None
            self.timer['end'] = time.time()

            self.sessions_log.append({
                'url': url,
                'code': '',
                'response': None,
                'time': time.ctime(),
                'error': error if 'error' in locals() else None,
                'connection_time': self.timer['end'] - self.timer['start']
            })

            if self.error_delay != 0.0:
                self.sleep(self.error_delay)
            count += 1
            if count == 7:
                raise MaxRequestsExceed

    @staticmethod
    def sleep(timeout):
        time.sleep(timeout)

    def make_request(self, method, url, *args, **kwargs):
        return super(PowerSession, self).request(method, url, *args, **kwargs)

    def get_domain(self, url=None, pure=False, pure_www=False):
        """
        pure=False    ->       https://www.google.com
        pure=True     ->       google.com
        pure_www=True ->       www.google.com
        """
        if not url:

            if getattr(self.last_response, 'url', False):
                return self.get_domain(url=self.last_response.url, pure=pure, pure_www=pure_www)
            else:
                return None

        if pure_www:
            return urlparse(url).netloc  # www.google.com
        if pure:
            return urlparse(url).netloc.replace('www.', '')  # google.com
        return f'https://{urlparse(url).netloc}'  # ex. https://www.google.com

    def soupize(self, text):
        if text:
            return BeautifulSoup(text, self.parser)
