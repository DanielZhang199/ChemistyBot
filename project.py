'''
title: Discord bot
author: Daniel Zhang
data-created: 2021-06-11
'''
# embed colors: https://coolors.co/3f4b3b-44633f-5a9367-5cab7d-4adbc8
import os
import pathlib
import sqlite3

import discord
# py -m pip install -U python-dotenv (not required) | py -m pip install -U discord.py
from dotenv import load_dotenv  # for keeping the bot token secure (just add a token in code for handing in)
from discord.ext import commands

Bot = commands.Bot(command_prefix='+')
DATABASE = 'project.db'
PERIODIC_TABLE = 'periodic_table.csv'  # as taken from Alberta Education chemistry data booklet

@Bot.event
# all events must be asynchronous (so all of the program code will be written asynchronously)
async def on_ready():
    await Bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name='to your every command')
    )
    print(f"{Bot.user} is online")


@Bot.event
async def on_disconnect():
    print(f"{Bot.user} has disconnected")


# coroutines (triggered by events)

@Bot.command(name='commands')
async def help_message(ctx):
    embed = discord.Embed(title="Untitled Discord Bot",
                          description="A bot that doesn't really do anything (yet) besides take up processor power.",
                          color=5935975)
    embed.add_field(name="Basic Commands",
                    value='''
```
+help: Shows this message
+hello: Say hello!
+say (text): Say whatever is after the command
```
                        ''',
                    inline=False)
    embed.add_field(name="Actual Commands (WIP)",
                    value='''
```
+data (Element/Ion) (symbol): Get data of element or ion
    - +database write (Ion): Adds data

+balance (equation): Balances equations

+calculate: Chemistry calculator
    - +calculate stoichiometry
    - +calculate gas
    - +calculate moles
```
                            ''',
                    inline=False)
    await ctx.send(embed=embed)


@Bot.command(name='hello')  # say hello back
async def hello(ctx):
    await ctx.send(f"Hello! {ctx.author.mention}")


@Bot.command(name='say')  # repeat all arguments given after command
async def say(ctx):
    await ctx.send(ctx.message.content[4:])

@Bot.command(name='data')
async def database(ctx, type = 'None', arg = 'None'):
    # variables are given default values of 'None' so that error messages can be displayed
    arg = arg[:2].capitalize()
    if type.lower().startswith("e"):
        embed = await read_element(arg)
        if embed is None:
            await ctx.send("```Could not find element data. Make sure you are entering only the element symbol in the command.```")
        else:
            await ctx.send(embed=embed)
    elif type.lower().startswith('i'):
        pass
    else:
        await ctx.send("```Invalid command format, type '+commands' for list of commands```")

# coroutines (functions triggered by bot commands)

# outputs
async def read_element(search):
    global CURSOR
    data = CURSOR.execute("SELECT * FROM elements WHERE symbol = ? ;", [search]).fetchone()
    if not data == None:
        result = []
        for i in range(len(data)):
            if data[i] == '':
                result.append('N/A')
            else:
                result.append(data[i])
        embed = discord.Embed(title=result[0],
                              description=f'''
    Symbol: {result[1]}
    Atomic Number: {result[2]}
    Ionic Charge: {result[3]}
    Molar Mass: {result[4]}
    Group: {result[5]}
    Electronegativity: {result[6]}
    State (SATP): {result[7]}
    ''',
                              color=4481855)
        return embed
    else:
        return None
# subroutines
# processing

def get_table(table):
    file = open(table)
    content = file.readlines()
    content.pop(0)
    for i in range(len(content)):
        content[i] = content[i].split(',')
        content[i][-1] = content[i][-1][:-1]
        for j in range(len(content[i])):
            if content[i][j].isnumeric():
                content[i][j] = int(content[i][j])
            else:
                try:
                    content[i][j] = float(content[i][j])
                except ValueError:
                    pass
    return content


if __name__ == "__main__":
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')  # replace with bot token later, token is currently stored in .env

    if not (pathlib.Path.cwd() / DATABASE).exists(): # create tables
        CONNECTION = sqlite3.Connection(DATABASE)
        CURSOR = CONNECTION.cursor()
        print("Initializing Database")
        CURSOR.execute(''' CREATE TABLE elements(
        name TEXT NOT NULL, symbol TEXT NOT NULL, atomic_number INTEGER PRIMARY KEY, charge TEXT,
        molar_mass TEXT NOT NULL, group_name TEXT NOT NULL, electronegativity REAL, state TEXT NOT NULL);''')
        # while all molar masses are REAL values, they are stored as text to keep significant figures

        # filling table
        ElementData = get_table(PERIODIC_TABLE)
        for i in range(len(ElementData)):
            CURSOR.execute('INSERT INTO elements VALUES(?, ?, ?, ?, ?, ?, ?, ?)  ;', ElementData[i])
        CONNECTION.commit()
        print("Finished loading periodic table")

    else:
        CONNECTION = sqlite3.Connection(DATABASE)
        CURSOR = CONNECTION.cursor()

    Bot.run(TOKEN)
