
import discord

Client = discord.Client()
TOKEN = 'ODUyOTUzODc5NTYxMjQwNjA3.YMOVNA.CylebfI5qt1qoGqj0RLKaJZjNCg'

@Client.event
async def on_ready():
    print(f"{Client.user} has connected.")

@Client.event
async def on_message(message):
    if message.author == Client.user:
        return
    if message.content.startswith('$hello'):
        await message.channel.send("Hello!")

# if __name__ == "__main__":
Client.run(TOKEN)