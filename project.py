'''
title: Discord bot
author: Daniel Zhang
data-created: 2021-06-11
'''

import os
import discord
# py -m pip install -U python-dotenv (not required) | py -m pip install -U discord.py
from dotenv import load_dotenv  # for keeping the bot token secure (just add a token in code for handing in)


load_dotenv()
Client = discord.Client()
TOKEN = os.getenv('DISCORD_TOKEN')  # replace with bot token later, token is currently stored in .env
toggle = False


@Client.event
# all events must be asynchronous (so all of the program code will be written asynchronously)
async def on_ready():
    await Client.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name='to your every command')
    )
    print(f"{Client.user} is online")


@Client.event
async def on_disconnect():
    print(f"{Client.user} has disconnected")


@Client.event
async def on_message(message):
    global toggle
    text = message.content
    if message.author == Client.user:  # there is an individual who loves spamming the bot on my testing server
        return
    elif text.startswith('+help'):  # all commands are here
        await print_help_message(message)

    elif text.startswith('+spam'):
        if not toggle:
            toggle = True
        else:
            toggle = False

    elif text.startswith('+hello'):  # just testing some basic I/O functions
        await message.channel.send(f"Hello! {message.author.mention}")
    elif text.startswith('+say'):

        await message.channel.send(f"{text[4:]}")

    elif message.author.mention != "<@!308971649070268416>" and toggle:
        await message.channel.send(f"Hello! {message.author.mention}")

# coroutines


async def print_help_message(message):  # kind of like an intro message, but only outputs when called
    embed = discord.Embed(title="Untitled Discord Bot",
                          description=f"A bot that doesn't really do anything (yet) besides take up processor power.",
                          color=3447003)
    embed.add_field(name="Basic Commands",
                    value='''
```
+help: Shows this message
+hello: Say hello!
+say <text>: Say whatever is after the command
```
                    ''',
                    inline=False)
    embed.add_field(name="Actual Commands (WIP)",
                    value='''
```
+database <Element>: Get element (or polyatomic ion) data
    - +database write <Ion>: Adds data for new ion
    
+balance <Equation>: Balances equations

+calculate: Chemistry calculator
    - +calculate stoichiometry
    - +calculate gas
    - +calculate moles
```
                        ''',
                    inline=False)
    await message.channel.send(embed=embed)


if __name__ == "__main__":
    Client.run(TOKEN)
