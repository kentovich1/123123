import asyncio


class DataQueue:
    def __init__(self):
        self.queue = []
        self.lock = asyncio.Lock()

    async def add_data(self, data):
        self.queue.append(data)

    async def get_data(self):
        async with self.lock:
            if len(self.queue) == 0:
                try:
                    with open('numbers.txt', 'r') as file:
                        lines = file.readlines()
                        if len(lines) < 1:
                            return None
                        line = lines.pop(0)
                        self.queue.append(line.replace('\n', ''))

                    with open('numbers.txt', 'w') as file:
                        file.writelines(lines)
                except FileNotFoundError:
                    return None

            if len(self.queue) > 0:
                return self.queue.pop(0)
            else:
                return None
