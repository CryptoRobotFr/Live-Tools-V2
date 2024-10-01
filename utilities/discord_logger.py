import aiohttp
import json

class DiscordLogger:
    def __init__(self, webhook_url: str=None):
        self.webhook_url = webhook_url
        self.messages = []

    def log(self, message: str):
        print(message)
        self.messages.append(message)

    async def send_discord_message(self, level: str = "INFO"):
        if self.webhook_url is None or self.webhook_url == "":
            return
        
        message_to_send = "\n".join(self.messages)
        color = 0
        if level == "INFO":
            color = 65280
        elif level == "WARNING":
            color = 16776960
        elif level == "ERROR":
            color = 16711680

        data = {
            "embeds": [{
                "title": f"{level} - Trading Bot Message",
                "description": str(message_to_send),
                "color": color,
                "thumbnail": None
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            await session.post(
                self.webhook_url,
                data=json.dumps(data),
                headers={"Content-Type": "application/json"}
            )

    async def send_now(self, message: str, level: str = "INFO"):
        print(message)
        if self.webhook_url is None or self.webhook_url == "":
            return
        
        message_to_send = message
        color = 0
        if level == "INFO":
            color = 65280
        elif level == "WARNING":
            color = 16776960
        elif level == "ERROR":
            color = 16711680

        data = {
            "embeds": [{
                "title": f"{level} - Trading Bot Message",
                "description": str(message_to_send),
                "color": color,
                "thumbnail": None
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            await session.post(
                self.webhook_url,
                data=json.dumps(data),
                headers={"Content-Type": "application/json"}
            )


