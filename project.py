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

Bot = commands.Bot(command_prefix='+', help_command=None)
DATABASE = 'project.db'
PERIODIC_TABLE = 'periodic_table.csv'  # as taken from Alberta Education chemistry data booklet
POLYATOMIC_IONS = 'polyatomic_ions.csv'

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

@Bot.command(name='help')  # custom help command
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
+database (Element/Ion) (symbol): Get data of element or ion
    - +database write (ion name) (ion formula) (charge)

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


@Bot.command(pass_context = True , aliases=['data', 'database', 'd'])
async def output_database(ctx, table='None', arg='None'):
    # variables are given default values of 'None' so that error messages can be displayed
    if table.lower().startswith("e"):  # search periodic table for element
        arg = arg[:2].capitalize()
        embed = await read_element(arg)  # await search to return from database
        if embed is None:  # if read_element returns empty
            await ctx.send("```Could not find element data.```")
        else:
            await ctx.send(embed=embed)
    elif table.lower().startswith('i'):  # search for ion
        embed = await read_ion(arg)
        if embed is None:  # if read_element returns empty
            await ctx.send("```Could not find ion in database, add new ion with +data write. (NOTE: Ion names are case-sensitive.)```")
        else:
            await ctx.send(embed=embed)
    else:
        await ctx.send("```Invalid command format, type '+commands' for list of commands```")

# @Bot.command(name='d')
# async def database_alt_name(ctx, table='None', arg='None'):
#     await database.invoke(ctx)


# coroutines (functions triggered by bot commands)

# outputs
async def read_element(search):
    global CURSOR
    data = CURSOR.execute("SELECT * FROM elements WHERE symbol = ? ;", [search]).fetchone()
    if data is not None:  # get data into list from tuple
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


async def read_ion(search):  # simliar code to read_element
    global CURSOR
    data = CURSOR.execute("SELECT * FROM ions WHERE formula = ? ;", [search]).fetchone()
    if data is not None:
        result = []
        for i in range(len(data)):
            if data[i] == '':
                result.append('N/A')
            else:
                result.append(data[i])
        embed = discord.Embed(title=result[0],
                              description=f'''
    Formula: {result[1]}
    Charge: {result[2]}
    Molar Mass: {result[3]}
    ''',
                              color=4481855)
        return embed
    else:
        return None
# subroutines
# processing


def load_elements(table):
    file = open(table)
    content = file.readlines()
    content.pop(0)  # delete table header
    for i in range(len(content)):
        content[i] = content[i].split(',')
        content[i][-1] = content[i][-1][:-1]  # split each row into 2D array
    print("Initializing element database")
    CURSOR.execute(''' CREATE TABLE elements(
    name TEXT NOT NULL, symbol TEXT NOT NULL, atomic_number INTEGER PRIMARY KEY, charge TEXT,
    molar_mass TEXT NOT NULL, group_name TEXT NOT NULL, electronegativity REAL, state TEXT NOT NULL);''')
    # while all molar masses are REAL values, they are stored as text to keep significant figures

    # filling table
    for i in range(len(content)):
        CURSOR.execute('INSERT INTO elements VALUES(?, ?, ?, ?, ?, ?, ?, ?)  ;', content[i])
    CONNECTION.commit()
    print("Finished loading periodic table")


def load_ions(table):  # almost the same code as above
    file = open(table)
    content = file.readlines()
    content.pop(0)  # delete table header
    for i in range(len(content)):
        content[i] = content[i].split(',')
        content[i][-1] = content[i][-1][:-1]  # split each row into 2D array and delete newline symbol
        print(molar_mass(content[i][1]))
        content[i][1], content[i][3] = molar_mass(content[i][1])
    print("Initializing ion database")
    CURSOR.execute("CREATE TABLE ions(name TEXT NOT NULL, formula TEXT NOT NULL, charge INTEGER NOT NULL, molar_mass TEXT NOT NULL);")

    # filling table
    for i in range(len(content)):
        CURSOR.execute('INSERT INTO ions VALUES(?, ?, ?, ?)  ;', content[i])
    CONNECTION.commit()
    print("Finished loading polyatomic ions")


def molar_mass(formula):
    '''
    takes a molecule and returns its molar mass and list of elements/coefficients
    :param formula: (str) Formula i.e. C6H5COO, C6H12O6
    :return: (str) Parsed formula, (float) molar mass
    '''
    global CURSOR
    parsed_formula = []
    total = 0
    for i in range(len(formula)):  # each letter can be upper case, lower case or a number
        coeff = None
        element = None
        if formula[i].isupper():  # the letter is capital (start of new element)
            try:  # we don't know if there are any more letters in the string
                if formula[i + 1].islower():  # the letter after is lowercase (two letter elements)
                    element = formula[i:(i + 2)]
                    try:
                        if formula[i + 2].isnumeric():  # check if next number is coefficient
                            j = i + 2
                            while formula[j].isnumeric():
                                if j + 1 < len(formula):
                                    j = j + 1
                                else:
                                    j = j + 1
                                    break
                            coeff = formula[i + 2:j]
                    except IndexError:
                        pass
                elif formula[i + 1].isnumeric():
                    j = i + 1
                    while formula[j].isnumeric():
                        if j + 1 < len(formula):
                            j = j + 1
                        else:
                            j = j + 1
                            break
                    element = formula[i]
                    coeff = formula[i + 1:j]
                elif formula[i + 1].isupper():  # next element, no coefficient
                    element = formula[i]
            except IndexError:
                element = formula[i]

            # add to parsed formula
            if coeff is None:
                coeff = 1
                parsed_formula.append(element)
            if coeff != 1:
                parsed_formula.append(element + str(coeff))

            # search element database for mass
            mass = CURSOR.execute("SELECT molar_mass FROM elements WHERE symbol = ?", [element]).fetchone()
            if mass is None:
                return None
            mass = mass[0]
            if mass.startswith('('):  # if mass is in brackets
                mass.pop(0)
                mass.pop(-1)
            total = total + (float(mass) * int(coeff))
    return ''.join(parsed_formula), total


if __name__ == "__main__":
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')  # replace with bot token later, token is currently stored in .env

    if not (pathlib.Path.cwd() / DATABASE).exists(): # create tables
        CONNECTION = sqlite3.Connection(DATABASE)
        CURSOR = CONNECTION.cursor()
        load_elements(PERIODIC_TABLE)
        load_ions(POLYATOMIC_IONS)

    else:
        CONNECTION = sqlite3.Connection(DATABASE)
        CURSOR = CONNECTION.cursor()

    Bot.run(TOKEN)
