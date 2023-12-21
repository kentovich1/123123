import asyncio
import logging

from checker_service import Checker
from config import threads
from data_class import DataQueue
from sms_hub_service import SmsHubService

client = SmsHubService()
data_queue = DataQueue()
logging.basicConfig(
    level=logging.DEBUG,
    format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
)


async def main():
    checker = Checker(data_queue=data_queue)
    tasks = []
    for _ in range(threads):
        tasks.append(checker.checker_worker())

    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())
