import asyncio
import logging
import random
import re
import string
from functools import lru_cache

from curl_cffi.requests import Session, Response

from models import GosUser


def from_line_to_gos_user(line: str) -> GosUser:
    fractions = line.split('|')
    for fraction in fractions:
        key = str(fraction.split(':')[0])[1:]
        if key not in ['ФИО', 'Выдано', 'Серия и номер паспорта']:
            value = fraction.split(':')[1].replace(' ', '')
        else:
            value = fraction.split(':')[1]
        if key == 'ФИО':
            fullname_fractions = [item for item in value.split(' ') if item != '']
            lastname = fullname_fractions[0]
            name = fullname_fractions[1]
            patronymic = fullname_fractions[2]
            fullname = f'{lastname} {name} {patronymic}'
        elif key == 'Пол':
            sex = value
        elif key == 'Дата рождения':
            dateBirthday = value.replace('-', '.')
        elif key == 'Код подразделения':
            codePassport = str(value)[:3] + '-' + str(value[3:])
        elif key == 'ИНН':
            inn = value
        elif key == 'Дата выдачи':
            datePassport = value.replace('-', '.')
        elif key == 'Выдано':
            value = value[1:]
            value = value[:len(value) - 2]
            wherePassport = value
        elif key == 'Место рождения':
            placeBirthday = value
        elif key == 'Серия и номер паспорта':
            value = value[1:]
            serialPassport = value.split(' ')[0]
            numberPassport = value.split(' ')[1]

    user = GosUser(fullname=fullname,
                   lastname=lastname,
                   name=name,
                   patronymic=patronymic,
                   sex=sex,
                   dateBirthday=dateBirthday,
                   wherePassport=wherePassport,
                   placeBirthday=placeBirthday,
                   serialPassport=serialPassport,
                   numberPassport=numberPassport,
                   datePassport=datePassport,
                   inn=inn,
                   codePassport=codePassport)
    return user


def get_normalized_phone(number: str) -> str:
    phone_number_pattern = r"(\d{3})(\d{3})(\d{2})(\d{2})"
    formatted_phone_number = re.sub(phone_number_pattern, r"(\1) \2-\3-\4", number)
    return formatted_phone_number


def generate_random_symbols(n=32):
    symbols = string.ascii_letters + string.digits
    random_symbols = ''.join(random.choice(symbols) for _ in range(n))
    return random_symbols


class MigServiceRegister:
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
                 user: GosUser):
        self.user: GosUser = user

    async def post_request(self,
                           url: str,
                           payload: str) -> Response:
        try:
            response = self.session.post(url, headers=self.headers,
                                         json=payload)
            if response.status_code != 200:
                await asyncio.sleep(1)
                return await self.post_request(url=url,
                                               payload=payload)
        except:
            await asyncio.sleep(1)
            return await self.post_request(url=url,
                                           payload=payload)
        return response

    async def get_request(self,
                          url: str) -> Response:
        try:
            response = self.session.get(url=url,
                                        headers=self.headers)
            if response.status_code != 200:
                await asyncio.sleep(1)
                return await self.get_request(url=url)
        except:
            await asyncio.sleep(1)
            return await self.get_request(url=url)
        return response

    async def get_where_passport_by_code(self,
                                         code: str) -> str:
        url = "https://pad-api.migcredit.ru/api/dadata/promtPassport"
        payload = {"query": code.replace('-', '')}
        response = await self.post_request(url=url, payload=payload)

        # logging.debug the response status code and content
        logging.debug(f"Where passport status Code: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(response.text)

        return response.json().get('payload').get('documentList')[0].get('issued')

    async def request_token(self):
        url = "https://pad-api.migcredit.ru/api/v1/getToken"
        response = await self.get_request(url=url)
        token = response.json().get('payload').get('token')
        refresh_token = response.json().get('payload').get('refreshToken')
        logging.debug(f"Got token status: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(token)
        logging.debug(refresh_token)
        self.headers["authorization"] = f"Bearer {token}"

    async def request_reg_1(self,
                            number: str):
        url = "https://pad-api.migcredit.ru/api/v1/creditApplication/dengi3/createOrder"
        payload = {
            "fullname": self.user.fullname,  # from user
            "lastname": self.user.lastname,  # from user
            "name": self.user.name,  # from user
            "patronymic": self.user.patronymic,  # from user
            "regionResidence": "7700000000000",  # random (Moscow)
            "dateBirthday": self.user.dateBirthday,  # from user
            "email": f"{generate_random_symbols(n=15)}@mail.ru",  # random
            "mobilePhone": get_normalized_phone(number=number),  # (999) 598-21-90
            "sex": self.user.sex,  # from user
            "acceptPD": True,
            "sum": "14000",
            "term": {
                "value": 21,
                "termUnit": "Day"
            },
            "ABTest": {
                "612": {
                    "Value": random.random(),
                    "Way": "A"
                },
                "1216": {
                    "Value": random.random(),
                    "Way": "B"
                },
                "1938": {
                    "Value": random.random(),
                    "Way": "B"
                },
                "2117": {
                    "Value": random.random(),
                    "Way": "A"
                },
                "2807": {
                    "Value": random.random(),
                    "Way": "A"
                }
            },
            "juicyLabsSession": "",
            "par2": "a",
            "pixel_user_fp": "",
            "pixel_sess_id": "",
            "personalDataProcessAllowed": True,
            "smsNotificationAllowed": True,
            "dfpId": "",
            "dfpType": "",
            "mobileDeviceParameters": {},
            "isMa20": False
        }
        response = await self.post_request(url=url, payload=payload)

        # logging.debug the response status code and content
        logging.debug(f"Reg 1 status Code: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(response.text)

    async def get_ucdb_id(self):
        url = "https://pad-api.migcredit.ru/api/v1/creditApplication/dengi3/getUCDB_ID"
        response = await self.get_request(url=url)
        # logging.debug the response status code and content
        logging.debug(f"UCDB status Code: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(response.text)

    async def get_init(self):
        url = "https://pad-api.migcredit.ru/api/v1/creditApplication/dengi3/init"
        response = await self.get_request(url=url)
        # logging.debug the response status code and content
        logging.debug(f"Get init status Code: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(response.text)

    async def get_couca_100(self):
        url = "https://pad-api.migcredit.ru/api/v1/creditApplication/dengi3/couca_100"
        response = await self.get_request(url=url)
        # logging.debug the response status code and content
        logging.debug(f"Couca 100 status Code: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(response.text)

    async def get_client_loyality(self):
        url = 'https://pad-api.migcredit.ru/api/v1/creditApplication/dengi3/getClientLoyalty'
        payload = {"isFinal": False}
        response = await self.post_request(url=url, payload=payload)
        # logging.debug the response status code and content
        logging.debug(f"Loyality status Code: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(response.text)

    async def get_couca_3_7(self):
        url = "https://pad-api.migcredit.ru/api/v1/creditApplication/dengi3/couca_3_7"
        response = await self.get_request(url=url)
        # logging.debug the response status code and content
        logging.debug(f"Couca 3.7 status Code: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(response.text)

    async def get_couca_3_5(self):
        url = "https://pad-api.migcredit.ru/api/v1/creditApplication/dengi3/couca_3_5"
        response = await self.get_request(url=url)
        # logging.debug the response status code and content
        logging.debug(f"Couca 3.5 status Code: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(response.text)

    async def get_couca_3_4_1(self):
        url = "https://pad-api.migcredit.ru/api/v1/creditApplication/dengi3/couca_3_4_1"
        response = await self.get_request(url=url)
        # logging.debug the response status code and content
        logging.debug(f"Couca 3.4.1 status Code: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(response.text)

    async def request_reg_2(self):
        url = "https://pad-api.migcredit.ru/api/v1/creditApplication/dengi3/savePassportAndAddress"

        payload = {
            "placeBirthday": self.user.dateBirthday,  # from user
            "wherePassport": await self.get_where_passport_by_code(code=self.user.codePassport),  # func from mark,
            "codePassport": self.user.codePassport,  # from user
            "datePassport": self.user.datePassport,  # from user
            "address": {
                "registration": {
                    "addressName": "г Москва, шоссе Энтузиастов",
                    "country": "Российская Федерация",
                    "postalCode": None,
                    "region": "Москва",
                    "fiasAddressRegionCode": "0c5b2444-70a0-4932-980c-b4dc0d3f02b5",
                    "regionType": "г",
                    "regionWithType": "г Москва",
                    "regionISOCode": "RU-MOW",
                    "regionTypeFull": "город",
                    "kladrAddressRegionCode": "7700000000000",
                    "district": None,
                    "fiasAddressDistrictCode": None,
                    "kladrAddressDistrictCode": None,
                    "districtType": None,
                    "districtTypeFull": None,
                    "districtWithType": None,
                    "city": "Москва",
                    "fiasAddressCityCode": "0c5b2444-70a0-4932-980c-b4dc0d3f02b5",
                    "kladrAddressCityCode": "7700000000000",
                    "cityType": "г",
                    "cityTypeFull": "город",
                    "cityWithType": "г Москва",
                    "street": "шоссе Энтузиастов",
                    "fiasAddressStreetCode": "b7e41003-6763-42b6-9d58-d61c2ce01144",
                    "kladrAddressStreetCode": "77000000000033000",
                    "streetType": "ш",
                    "streetTypeFull": "шоссе",
                    "streetWithType": "шоссе Энтузиастов",
                    "settlement": None,
                    "fiasAddressSettlementCode": None,
                    "kladrAddressSettlementCode": None,
                    "settlementType": None,
                    "settlementTypeFull": None,
                    "settlementWithType": None,
                    "house": "1",
                    "fiasAddressHouseCode": None,
                    "kladrAddressHouseCode": None,
                    "houseType": None,
                    "houseTypeFull": None,
                    "blockType": None,
                    "housingTypeFull": None,
                    "buildingTypeFull": None,
                    "fiasAddressFlatCode": None,
                    "apartmentType": None,
                    "apartmentTypeFull": None,
                    "kladrCode": "Y",
                    "okatoCode": "45000000000",
                    "punkt": "г Москва",
                    "punktCode": "0c5b2444-70a0-4932-980c-b4dc0d3f02b5",
                    "regionText": "г Москва"
                }
            },
            "numberPassport": self.user.numberPassport,  # from user
            "serialPassport": self.user.serialPassport,  # from user
            "snils": None,
            "inn": None  # self.user.inn  # from user
        }
        response = await self.post_request(url=url, payload=payload)

        # logging.debug the response status code and content
        logging.debug(f"Reg 2 status code: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(response.text)

    async def request_send_code(self):
        url = "https://pad-api.migcredit.ru/api/v1/creditApplication/dengi3/sendSms"
        response = await self.get_request(url=url)

        # logging.debug the response status code and content
        logging.debug(f"Send code status code: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(response.text)

    async def request_send_otp(self,
                               code: str):
        url = "https://pad-api.migcredit.ru/api/v1/creditApplication/dengi3/checkSms"
        payload = {
            "code": code,
            "edsAllowed": True,
            "insuranceAllowed": True,
            "autopay": True,
            "bkiNotificationAllowed": True,
            "cessionAllowed": True,
            "bancrotFlag": True
        }
        response = await self.post_request(url=url, payload=payload)

        # logging.debug the response status code and content
        logging.debug(f"Send otp status code: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(response.text)

    async def request_send_work(self):
        url = "https://pad-api.migcredit.ru/api/v1/creditApplication/dengi3/saveWorkAndContact"

        payload = {
            "typeWork": "Military",
            "companyView": "",
            "incomeWork": 98000,
            "contactsStatus": "",
            "contactsPhone": "",
            "snils": None,
            "inn": self.user.inn
        }

        response = await self.post_request(url=url, payload=payload)

        # logging.debug the response status code and content
        logging.debug(f"Send work status code: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(response.text)

    async def get_status(self):
        url = 'https://pad-api.migcredit.ru/api/v1/creditApplication/dengi3/getStatus'
        response = await self.get_request(url=url)
        # logging.debug the response status code and content
        logging.debug(f"Get status status Code: {response.status_code}")
        logging.debug("Response Content:")
        logging.debug(response.text)
        return response

    async def wait_for_final_status(self):
        data = await self.get_status()
        while not data.json().get('payload').get('isFinalStatus'):
            await asyncio.sleep(2)
            data = await self.get_status()
        return True

# async def main():
#     user = from_line_to_gos_user(line=line)
#     mig_service = MigServiceRegister(user=user)
#     await mig_service.request_token()
#     await mig_service.request_reg_1(number='9377608614')
#
#     await mig_service.get_init()
#     await mig_service.get_ucdb_id()
#     await mig_service.get_couca_100()
#     await mig_service.get_client_loyality()
#
#     await mig_service.request_reg_2()
#     await mig_service.get_couca_3_4_1()
#     await mig_service.request_send_code()
#     code = input('Input code: ')
#     await mig_service.request_send_otp(code=code)
#     await mig_service.get_couca_3_5()
#     await mig_service.request_send_work()
#     await mig_service.get_couca_3_7()
#     await mig_service.wait_for_final_status()
