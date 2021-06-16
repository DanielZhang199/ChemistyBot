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


# coroutines (events)

@Bot.event
async def on_ready():
    await Bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name='your every command | +help')
    )
    print(f"{Bot.user} is online")


@Bot.event
async def on_disconnect():
    print(f"{Bot.user} has disconnected")

# inputs/outputs


@Bot.command(name='help', aliases=['h', 'commands'])  # custom help command
async def help_message(ctx):
    embed = discord.Embed(title="Untitled Discord Bot",
                          description='''A bot that doesn't really do anything (yet) besides take up processor power. 
Data was taken from Alberta Chemistry 30 Data Booklet. 
(https://www.alberta.ca/assets/documents/edc-chemistry30-data-booklet.pdf)''',
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
+database (Element / Ion) (symbol): Get element/ion data
    +database add (ion name) (ion formula) [charge]
    +database delete (ion name)```
```+balance (equation): Balances equations```
```+convert (value) (conversion):
    +convert help: supported conversion list```
```+calculate:
    +calculate stoichiometry [help]
    +calculate gas
    +calculate moles```
```+soluble (formula)```
                            ''',
                    inline=False)
    await ctx.send(embed=embed)


@Bot.command(name='hello')  # say hello back
async def hello(ctx):
    await ctx.send(f"Hello! {ctx.author.mention}")


@Bot.command(name='say')  # repeat all arguments given after command
async def say(ctx):
    await ctx.send(ctx.message.content[4:])


@Bot.command(name='database', aliases=['data', 'dat', 'd'])  # reading, writing, deleting from database
async def output_database(ctx, subcmd=None, arg1=None, arg2=None, arg3=None):  # takes context, subcommand, and 3 arguements
    # variables are given default values of 'None' so that error messages can be displayed

    if subcmd.lower().startswith("e"):  # search periodic table for element
        arg1 = arg1[:2].capitalize()
        embed = read_element(arg1)
        if embed is None:  # if read_element returns empty
            await ctx.send("```Could not find element data.```")
        else:
            await ctx.send(embed=embed)
    elif subcmd.lower().startswith('i'):  # search for ion
        embed = read_ion(arg1)
        if embed is None:  # if read_element returns empty
            await ctx.send("```Could not find ion in database. (Ion names are case-sensitive.)```")
        else:
            await ctx.send(embed=embed)

    elif subcmd.lower().startswith('a') or subcmd.lower().startswith('w') :  # adding ion (writing ion)
        try:  # in case of index error
            success = add_ion(arg1, arg2, arg3)  # outcome of write command
            if success == 'Success':
                await ctx.send(f"```Successfully added {arg1} to database```")
            elif success == 'Duplicate':
                embed = read_ion(arg2)
                await ctx.send("```Entry already exists within database; delete the entry first to modify it. | +data delete (formula)```",)
                await ctx.send(embed=embed)  # output ion data that is duplicated
            else:
                await ctx.send(f"```Invalid given formula: '{arg2}'```")
        except TypeError:
            await ctx.send('''```
Invalid command format: use +data write (name) (formula) (ionic charge)
Example: +data add Acetate CH3COO 1-```''')

    elif subcmd.lower().startswith('d'):  # deleting ion
        name = arg1
        delete_ion(name)  # delete any ions matching the first given argument
        if arg1 != '*':
            await ctx.send(f"```Successfully deleted {arg1} from database```")
        else:
            await ctx.send(f"```Successfully reloaded database```")
    else:
        await ctx.send("```Invalid command format | +commands for list of commands```")


@Bot.command(name='molar_mass', aliases=["mole", "m", "molarmass"])
async def calculate_mm(ctx, arg):
    formula, result = molar_mass(arg)
    formula = ''.join(formula)
    if not formula:  # could not read formula
        await ctx.send(f"```Invalid formula given: {arg} (Formulas are case-sensitive)```")
    else:
        formula = convert_subscript(formula)
        await ctx.send(f"```Molar mass of {formula}: {result} g/mol```")


@Bot.command(name='conversion', aliases=["convert", 'c', 'con'])
async def convert_unit(ctx, value='None', conversion='None'):  # parameter conversions must always be strings
    if value.lower().startswith("help"):  # list of conversions
        await ctx.send('''```
Command Format:
+conversion (value) (conversion)```
```
Supported Conversions:
> 'c-k'
> 'k-c'
> 'kpa-atm'
> 'atm-kpa
> 'kpa-mmhg'
> 'mmhg-kpa'
> 'mmhg-atm'
> 'atm-mmhg'```''')
        return
    try:
        value = float(value)
    except ValueError:
        await ctx.send("```Conversion value must be a number. | +convert help```")
        return
    if conversion.lower() == 'c-k':  # C>K
        await ctx.send(f"```{value}°C = {round(value + 273.15, 4)}K```")
    elif conversion.lower() == 'k-c':  # K>C
        await ctx.send(f"```{value}K = {round(value - 273.15, 4)}°C```")
    elif conversion.lower() == 'kpa-atm':
        await ctx.send(f"```{value}kPa = {round(value / 101.325, 6)}Atm```")
    elif conversion.lower() == 'atm-kpa':
        await ctx.send(f"```{value}Atm = {round(value * 101.325, 6)}kPa```")
    elif conversion.lower() == 'kpa-mmhg':
        await ctx.send(f"```{value}kPa = {round(value * 7.50062, 6)}mmHg```")
    elif conversion.lower() == 'mmhg-kpa':
        await ctx.send(f"```{value}mmHg = {round(value / 7.50062, 6)}kPa```")
    elif conversion.lower() == 'mmhg-atm':
        await ctx.send(f"```{value}mmHg = {round(value / 760, 6)}Atm```")
    elif conversion.lower() == 'atm-mmhg':
        await ctx.send(f"```{value}Atm = {round(value * 760, 6)}mmHg```")
    else:
        await ctx.send(f"```Could not find requested conversion | +convert help to show list of conversions```")


# subroutines
# processing (input and outputs are async commands listen earlier)

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


def delete_ion(formula):
    global CURSOR, CONNECTION
    if formula == '*':  # not user function, just so I can reset database in case of mistakes
        print("Deleting and reloading databases")
        CURSOR.execute('DROP TABLE elements;')
        load_elements(PERIODIC_TABLE)
        CURSOR.execute('DROP TABLE ions;')
        load_ions(POLYATOMIC_IONS)
    else:
        CURSOR.execute('DELETE FROM ions WHERE formula = ?;', [formula])
        CONNECTION.commit()


def convert_subscript(text):   # subscript for formula numbers
    new_text = []
    for i in text:
        if i.isnumeric():
            i = Subscript[i]
        new_text.append(i)
    return ''.join(new_text)


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
        formula, content[i][3] = molar_mass(content[i][1])
        content[i][1] = ''.join(formula)
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
    :return: (list) Parsed formula, (float) molar mass
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
                mass = mass[1:-1]
            total = total + (float(mass) * int(coeff))
    return parsed_formula, round(total, 2)  # does not use significant digits (not enough time to implement)


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
    TOKEN = os.getenv('token')  # replace with: TOKEN = '{BOT_TOKEN}'

    if not (pathlib.Path.cwd() / DATABASE).exists(): # create tables
        CONNECTION = sqlite3.Connection(DATABASE)
        CURSOR = CONNECTION.cursor()
        load_elements(PERIODIC_TABLE)
        load_ions(POLYATOMIC_IONS)

    else:
        CONNECTION = sqlite3.Connection(DATABASE)
        CURSOR = CONNECTION.cursor()

    Bot.run(TOKEN)  # start main loop
