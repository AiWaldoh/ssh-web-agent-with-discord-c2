class MessageSender:
    async def send_message(self, page, message):
        if not message:
            print("Empty message. Skipping sending to Discord.")
            return

        message_chunks = self._split_message_into_chunks(message)
        await self._clear_textbox(page)

        for chunk in message_chunks:
            await self._type_and_send_chunk(page, chunk)

    def _split_message_into_chunks(self, message, max_length=1900):
        return [message[i : i + max_length] for i in range(0, len(message), max_length)]

    async def _clear_textbox(self, page):
        await page.click('div[role="textbox"]', click_count=3)
        await page.press('div[role="textbox"]', "Backspace")

    async def _type_and_send_chunk(self, page, chunk):
        lines = chunk.split("\n")
        for i, line in enumerate(lines):
            await page.type('div[role="textbox"]', line)
            if i < len(lines) - 1:
                await self._press_shift_enter(page)
            else:
                await page.keyboard.press("Enter")

    async def _press_shift_enter(self, page):
        await page.keyboard.down("Shift")
        await page.keyboard.press("Enter")
        await page.keyboard.up("Shift")
