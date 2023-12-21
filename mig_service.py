import logging

from curl_cffi.requests import Session, Response


class MigService:
    session = Session(impersonate="chrome110")

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.8",
        # "authorization": f"Bearer {token}",
        "connection": "keep-alive",
        "content-type": "application/json",
        "host": "pad-api.migcredit.ru",
        "origin": "https://form.migcredit.ru",
        "referer": "https://form.migcredit.ru/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "sec-ch-ua": "\"Brave\";v=\"119\", \"Chromium\";v=\"119\", \"Not?A_Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    def __init__(self,
                 number: str,
                 number_id: int):
        self.refresh_token = None
        self.number = number
        self.number_id = number_id

    async def post_request(self,
                           url: str,
                           payload: str) -> Response:
        try:
            response = self.session.post(url, headers=self.headers,
                                         json=payload)
            if response.status_code != 200:
                return await self.post_request(url=url,
                                               payload=payload)
        except:
            return await self.post_request(url=url,
                                           payload=payload)
        return response

    async def get_request(self,
                          url: str) -> Response:
        try:
            response = self.session.get(url=url,
                                        headers=self.headers)
            if response.status_code != 200:
                return await self.get_request(url=url)
        except:
            return await self.get_request(url=url)
        return response

    async def request_token(self):
        url = "https://pad-api.migcredit.ru/api/v1/getToken"
        response = await self.get_request(url=url)
        token = response.json().get('payload').get('token')
        refresh_token = response.json().get('payload').get('refreshToken')
        logging.debug(f"Got token status: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(token)
        logging.debug(refresh_token)
        self.refresh_token = refresh_token
        self.headers["authorization"] = f"Bearer {token}"


    async def check_loyalty_flag(self) -> bool:
        url = 'https://pad-api.migcredit.ru/api/v1/pad/getUserClient'
        response = await self.get_request(url=url)
        print(response.text)
        return response.json().get('payload').get('data').get('loyaltyFlag')

    async def send_code(self) -> int:
        url = "https://pad-api.migcredit.ru/api/v1/auth/sendCode"
        payload = {
            "phone": self.number[1:],
            "mode": "sms"
        }
        response = await self.post_request(url=url,
                                           payload=payload)
        print(response.text)
        if response.text == '{"payload":["sendCode not check"],"resultCode":"ERROR_ESB"}':
            return False
        return response.json().get('payload').get('callId')

    async def spoof_session(self,
                            number: str,
                            code: str,
                            call_id: int):
        url = "https://pad-api.migcredit.ru/api/v1/auth/checkCode"

        payload = {
            "phone": number,
            "code": code,
            "mode": "sms",
            "callId": call_id,
            "deviceType": "Stationary"
        }

        response = await self.post_request(url=url,
                                           payload=payload)
        if response.json().get('payload').get('responseMessage') == 'Uncorrect':
            return False
        logging.debug(response.text)
        return True
