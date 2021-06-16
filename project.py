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
Subscript = {"1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉", "0": "₀", }


# coroutines


@Bot.event
# all events must be asynchronous (so all of the program code will be written asynchronously)
async def on_ready():
    await Bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name='your every command | +help')
    )
    print(f"{Bot.user} is online")


@Bot.event
async def on_disconnect():
    print(f"{Bot.user} has disconnected")


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

# commands (input/output)


@Bot.command(name='hello')  # say hello back
async def hello(ctx):
    await ctx.send(f"Hello! {ctx.author.mention}")


@Bot.command(name='say')  # repeat all arguments given after command
async def say(ctx):
    await ctx.send(ctx.message.content[4:])


@Bot.command(pass_context = True , aliases=['data', 'database', 'd'])  # reading, writing, deleting from database
async def output_database(ctx, subcmd='None', *arg):  # takes context, subcommand, and all following arguments (tuple)
    # variables are given default values of 'None' so that error messages can be displayed
    if subcmd.lower().startswith("e"):  # search periodic table for element
        arg = arg[0]  # take first argument after the subcommand
        arg = arg[:2].capitalize()
        embed = read_element(arg)  # technically running sync code is bad practice, but it is highly unlikely for this function to take very long or crash
        if embed is None:  # if read_element returns empty
            await ctx.send("```Could not find element data.```")
        else:
            await ctx.send(embed=embed)
    elif subcmd.lower().startswith('i'):  # search for ion
        embed = read_ion(arg[0])
        if embed is None:  # if read_element returns empty
            await ctx.send("```Could not find ion in database; Ion names are case-sensitive. (Add new ion with +data write)```")
        else:
            await ctx.send(embed=embed)
    elif subcmd.lower().startswith('w'):
        try:
            success = add_ion(arg[0], arg[1], arg[2])  # outcome of write command
            if success == 'Success':
                await ctx.send(f"```Successfully added {arg[0]} to database```")
            elif success == 'Duplicate':
                await ctx.send("```Entry already exists within database```")
                embed = read_ion(arg[1])
                await ctx.send(embed=embed)  # output ion data that is duplicated
            else:
                await ctx.send(f"```Invalid formula: '{arg[1]}'```")
        except IndexError:
            await ctx.send('''```
Invalid command format, +data write (name) (formula) (ionic charge)
Example: +data write Acetate CH3COO 1-```''')
    else:
        await ctx.send("```Invalid command format, type '+commands' for list of commands```")


# subroutines
# technically it would be better to use async coroutines here too,
# but none of the functions take very long to execute for there to be a noticeable slowdown, (i think?)
# not sure if SQLite functions support await

# processing

# adding and deleting from ion database

def add_ion(name, formula, charge):
    name = name.capitalize()
    formula, mass = molar_mass(formula)
    if not formula:  # if molar_mass returned False (formula invalid)
        return False
    global CURSOR, CONNECTION
    try:
        CURSOR.execute('INSERT INTO ions VALUES(?, ?, ?, ?) ;', [name, formula, charge, mass])
        CONNECTION.commit()
        return 'Success'
    except sqlite3.IntegrityError:  # primary key (formula) not unique
        return 'Duplicate'


def convert_subscript(text):   # subscript for formula numbers
    for i in range(len(text)):
        if text[i].isnumeric():
            text = text.replace(text[i], Subscript[text[i]])
    return text


def load_elements(table):
    file = open(table)
    content = file.readlines()
    content.pop(0)  # delete table header
    for i in range(len(content)):
        content[i] = content[i].split(',')
        content[i][-1] = content[i][-1][:-1]  # split each row into 2D array and remove new line
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
    content.pop(0)
    for i in range(len(content)):
        content[i] = content[i].split(',')
        content[i][-1] = content[i][-1][:-1]
        content[i][1], content[i][3] = molar_mass(content[i][1])
    print("Initializing ion database")
    CURSOR.execute("CREATE TABLE ions(name TEXT NOT NULL, formula PRIMARY KEY, charge INTEGER NOT NULL, molar_mass TEXT NOT NULL);")

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
                            # check how many consecutive digits there are (so coefficient is not limited to one digit)
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
                return False, False  # return that the formula is invalid
            mass = mass[0]
            if mass.startswith('('):  # if mass is in brackets
                mass.pop(0)
                mass.pop(-1)
            total = total + (float(mass) * int(coeff))
    return ''.join(parsed_formula), round(total, 2)  # does not use significant digits (not enough time to implement)


def read_element(search):
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


def read_ion(search):  # similar code to read_element
    global CURSOR
    data = CURSOR.execute("SELECT * FROM ions WHERE formula = ? ;", [search]).fetchone()
    if data is not None:
        result = []
        for i in range(len(data)):
            if data[i] == '':
                result.append('N/A')
            else:
                result.append(data[i])

        result[1] = convert_subscript(result[1])  # converts coefficients to subscript

        embed = discord.Embed(title=result[0],
                              description=f'''
    Formula: {result[1]}
    Ionic Charge: {result[2]}
    Molar Mass: {result[3]}
    ''',
                              color=4148027)
        return embed
    else:
        return None


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
