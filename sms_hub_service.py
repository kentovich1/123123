import asyncio
import logging
import re

import httpx
from httpx import Response

from config import sms_hub_api


class SmsHubService:
    client = httpx.AsyncClient()

    def __init__(self):
        ...

    async def get_request(self,
                          url: str,
                          params: dict) -> Response:
        try:
            return await self.client.get(url=url,
                                         params=params)
        except:
            return await self.get_request(url=url,
                                          params=params)

    async def get_balance(self) -> float:
        url = 'https://smshub.org/stubs/handler_api.php'
        query = {
            'api_key': sms_hub_api,
            'action': 'getBalance',
        }

        response = await self.get_request(url=url,
                                          params=query)
        pattern = re.compile(r"ACCESS_BALANCE:(\d+\.\d+)")
        match = pattern.search(response.text)
        balance = match.group(1)
        return balance

    async def get_new_number(self) -> (int, int):
        url = 'https://smshub.org/stubs/handler_api.php'
        query = {
            'api_key': sms_hub_api,
            'action': 'getNumber',
            'service': 'ot',
            'country': '0',
            'maxPrice': '6'
        }

        response = await self.get_request(url=url,
                                          params=query)
        pattern = re.compile(r"ACCESS_NUMBER:(?P<id>\d+):(?P<number>\d+)")
        match = pattern.match(response.text)
        id = match.group('id')
        number = match.group('number')
        return id, number

    async def get_status_number(self,
                                id: int) -> str:
        url = 'https://smshub.org/stubs/handler_api.php'
        query = {
            'api_key': sms_hub_api,
            'action': 'getStatus',
            'id': id
        }
        try:
            response = await self.get_request(url=url,
                                              params=query)
            # zayebalsya
            print(response.text)
            data = response.text.split(':', 1)
            logging.debug(response.text)
            if data[0] == 'STATUS_OK':
                return data[1]
            elif data[0] == 'STATUS_WAIT_RETRY':
                await asyncio.sleep(5)
                return await self.get_status_number(id=id)
            elif data[0] == 'STATUS_CANCEL':
                return False
            elif data[0] == 'STATUS_WAIT_CODE':
                await asyncio.sleep(5)
                return await self.get_status_number(id=id)
        except:
            return await self.get_status_number(id=id)

    async def resend_number(self,
                            id: int):
        url = 'https://smshub.org/stubs/handler_api.php'
        query = {
            'api_key': sms_hub_api,
            'action': 'setStatus',
            'id': id,
            'status': 3
        }
        await self.get_request(url=url,
                               params=query)

    async def close_number(self,
                           id: int):
        url = 'https://smshub.org/stubs/handler_api.php'
        query = {
            'api_key': sms_hub_api,
            'action': 'setStatus',
            'id': id,
            'status': 8
        }
        await self.get_request(url=url,
                               params=query)
