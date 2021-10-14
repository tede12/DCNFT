import json
import time
import uuid

from config import Config
from libraries.logger import Logger
from libraries.request_utils import PowerSession
from libraries.telegram_send import send_telegram


class DcUniverse:
    def __init__(self):
        self.session = PowerSession(error_delay=10.0)
        self.log = Logger(logger_name='NFT_DCUNIVERSE', classic=True)

    def start(self):
        response = self.session.get(
            url='https://nft.dcuniverse.com/',
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "DNT": "1",
                "Host": "nft.dcuniverse.com",
                "Pragma": "no-cache",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:94.0) Gecko/20100101 Firefox/94.0"
            },
            timeout=12
        )

        # redirect to queue_it
        io_builder_queue_url = response.url
        if 'iobuilders.queue-it.net' not in io_builder_queue_url:
            self.log.error('Something went wrong with the request.')
            return

        # Request for "queue-it_log"
        response = self.session.get(io_builder_queue_url)
        queue_it_log = response.soup.find('meta', {'id': 'queue-it_log'})
        if queue_it_log:
            queue_it_log = queue_it_log.attrs.get('data-userid')

        if not queue_it_log:
            self.log.error('Can\'t find QUEUE_IT_LOG')
            return
        else:
            self.log.success(f'QUEUE_IT_LOG: u={queue_it_log}')

        # Request for "queueId"
        response = self.session.post(
            url='https://iobuilders.queue-it.net/spa-api/queue/iobuilders/dcpro/enqueue?cid=en-US',
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "application/json",
                "DNT": "1",
                "Host": "iobuilders.queue-it.net",
                "Origin": "https://iobuilders.queue-it.net",
                "Pragma": "no-cache",
                "Referer": io_builder_queue_url,
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "TE": "trailers",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:94.0) Gecko/20100101 Firefox/94.0",
                "X-Requested-With": "XMLHttpRequest"
            },
            cookies={
                "Queue-it": f"u={queue_it_log}"
            },
            json={
                "layoutName": "DCComics",
                "customUrlParams": "",
                "targetUrl": "https://nft.dcuniverse.com/",
                "Referrer": ""
            }

        )
        try:
            queue_id = response.json().get('queueId')
        except json.JSONDecodeError:
            queue_id = None

        if not queue_id:
            self.log.error('Can\'t find QUEUE_ID')
            return

        self.log.status(f"QueueID: {queue_id}")

        # Start Timings
        self.session.options(url='https://eu-west-1-perf-api.queue-it.net/perf/timings')
        if self.session.last_response.status_code != 200:
            self.log.error('Error on setting Timings')
            return

        self.log.status('OPTIONS timings OK')

        self.session.post(
            url='https://eu-west-1-perf-api.queue-it.net/perf/timings',
            json=[
                {"method": "GET", "requestType": "PAGE",
                 "pageUrl": "https://iobuilders.queue-it.net/",
                 "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:94.0) Gecko/20100101 Firefox/94.0",
                 "requestStart": int(time.time()), "responseStart": int(time.time()),
                 "responseEnd": int(time.time()),
                 "customerId": "iobuilders",
                 "tags": [
                     {"key": "eventid", "value": "dcpro"},
                     {"key": "queueid", "value": "00000000-0000-0000-0000-000000000000"},
                     {"key": "queueit", "value": "queue"}
                 ]
                 }
            ]
        )

        if self.session.last_response.status_code == 201:
            self.log.status('POST timings OK')

        redirect_target = None
        while 1:
            self.session.post(
                url=f'https://iobuilders.queue-it.net/spa-api/queue/iobuilders/dcpro/{queue_id}/status',
                params={
                    'cid': 'en-US',
                    'l': 'DCComics',
                    'seid': str(uuid.uuid1()),
                    'sets': int(time.time()) - 60 * 5
                },
                json={
                    "targetUrl": "https://nft.dcuniverse.com/",
                    "customUrlParams": "",
                    "layoutVersion": int(time.time()),
                    "layoutName": "DCComics",
                    "isClientRedayToRedirect": True,
                    "isBeforeOrIdle": False
                }
            )

            try:
                response_json = self.session.last_response.json()

                sleep_time = response_json.get('updateInterval')
                redirect_target = response_json.get('redirectUrl')

                queue_number = response_json.get('ticket', {}).get('queueNumber')
                user_in_line_ahead_me = response_json.get('ticket', {}).get('usersInLineAheadOfYou')
                time_text_missing = response_json.get('ticket', {}).get('whichIsIn')
                res = "OK" if self.session.last_response.ok else "ERROR"

                self.log.info(
                    f'Queue status: [{res}] Queue Number: {queue_number}, '
                    f'User Before Me: {user_in_line_ahead_me}. {time_text_missing}'
                )

                if not sleep_time and redirect_target:
                    break
                time.sleep(sleep_time / 1000)

            except json.JSONDecodeError:
                self.log.error('Error in Queue')
                break

        print('\n\n')

        self.log.success(redirect_target)

        if Config.USE_TELEGRAM:
            send_telegram(url=redirect_target)


if __name__ == '__main__':
    DcUniverse().start()
