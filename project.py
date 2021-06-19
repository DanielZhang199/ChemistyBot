'''
title: Discord bot
author: Daniel Zhang
data-created: 2021-06-11
'''
# last embed colour: 4905928
import os
import pathlib
import sqlite3
import re

import discord  # required dependency
from discord.ext import commands
# py -m pip install python-dotenv (not required) | py -m pip install discord.py
from dotenv import load_dotenv  # for keeping the bot token secure (just add a token in code for handing in)

try:
    from sympy import Matrix, lcm  # py -m pip install sympy
except ModuleNotFoundError:
    print("Dependencies required to preform equation balancing were not found, stoichometric functions will be unavailable")


Bot = commands.Bot(command_prefix='+', help_command=None)
DATABASE = 'project.db'
PERIODIC_TABLE = 'periodic_table.csv'  # as taken from Alberta Education chemistry data booklet
POLYATOMIC_IONS = 'polyatomic_ions.csv'
Subscript = {"1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉", "0": "₀", }

# Lists used as global variables for balancing
CoefficientMatrix = []
ElementList = []
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
    embed = discord.Embed(title="Chem-Bot",
                          description='''Bot that helps with chemistry and whilst taking up my processor power and RAM. 
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
                    value='''```
+database (Element / Ion) (symbol): Get element/ion data
    +database add (ion name) (ion formula) [charge]
    +database delete (ion name)```
```+balance (equation): Balances equations
        +balance help: formatting help (WIP)```
```+convert (value) (conversion):
    +convert help: shows supported conversion list```
```+calculate [help]: see detail
    +calculate stoichiometry  (WIP)
    +calculate gas 
    +calculate moles ```
```+solubility (positive ion) (negative ion)```
```+formulas: In case you are too lazy to find a formula sheet (WIP)```''',
                    inline=False)
    await ctx.send(embed=embed)


@Bot.command(name='hello')  # say hello back
async def hello(ctx):
    message = await ctx.send(f"Hello! {ctx.author.mention}")
    await message.add_reaction('\N{THUMBS UP SIGN}')


@Bot.command(name='say')  # repeat all arguments given after command
async def say(ctx):
    await ctx.send(ctx.message.content[4:])



@Bot.command(name='database', aliases=['data', 'dat', 'd'])  # reading, writing, deleting from database
async def output_database(ctx, subcmd='', arg1=None, arg2=None, arg3=None):  # takes context, subcommand, and 3 arguements
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
                await ctx.send("```Entry already exists within database; delete the entry first to modify it. | +data delete (formula)```")
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
        await ctx.send("```Invalid command format | +help for list of commands```")


@Bot.command(name='molar_mass', aliases=["mole", "m", "molarmass"])
async def calculate_mm(ctx, arg):
    formula, result = molar_mass(arg)
    formula = ''.join(formula)
    if not formula:  # could not read formula
        await ctx.send(f"```Invalid formula given: {arg} (Formulas are case-sensitive)```")
    else:
        formula = convert_subscript(formula)
        await ctx.send(f"```Molar mass of {formula}: {result} g/mol```")


@Bot.command(name='conversion', aliases=["convert", 'con'])
async def convert_unit(ctx, value='', conversion=''):  # parameters must always be strings
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


@Bot.command(name='solubility', aliases=["soluble", 'sol', 's'])
async def soluble(ctx, pos_ion, neg_ion):
    result = test_soluble(pos_ion, neg_ion)
    formula = balance_ionic(pos_ion, neg_ion)
    if formula is not False:
        if result:
            await ctx.send(f"```The ions {pos_ion} and {neg_ion} will form {formula}, which is soluble in water```")
        else:
            await ctx.send(f"```The ions {pos_ion} and {neg_ion} will form {formula}, which is not soluble in water```")
    else:
        if result:
            await ctx.send(f"```{pos_ion} and {neg_ion} will form a water soluble compound, but one or more ionic charges were not found in database.```")
        else:
            await ctx.send(f"```{pos_ion} and {neg_ion} will not form a water soluble compound, but one or more ionic charges were not found in database.```")


@Bot.command(name='calculate', aliases=["cal", 'calc'])
async def calculate(ctx, subcmd='', *args):  # *args returns a tuple of all arguments in command message after the first 2
    if subcmd.lower().startswith('h'):  # help command
        embed = discord.Embed(title="Calculations", color=6073213)
        embed.add_field(name="Gas Law | +calculate gas (p) (v) (n) (t)",
                        value='''```
p: pressure in kPa
v: volume of gas in L
n: moles of gas
t: temperature in K
Replace a parameter with a word (i.e 'find') to calculate for value. (Any other non numeric value will also work)
Example: +calculate gas 120 2.0 1.0 find```''',
                        inline=False)

        embed.add_field(name="Stoichiometry",
                        value='''```
WIP```''',
                        inline=False)
        embed.add_field(name="Molar Mass | +calculate mole (formula)",
                        value='''```
formula: Ionic compound formula (case-sensitive)```''',
                        inline=False)
        await ctx.send(embed=embed)

    elif subcmd.lower().startswith('g'):  # gas calculation
        # PV = nRT (takes 4 arguments)
        try:
            p = args[0]
            v = args[1]
            n = args[2]
            t = args[3]
        except IndexError:
            await ctx.send("```Incorrect number of parameters given | +calculate help```")
            return
        r = 8.314
        try:  # lots of error checking to figure out what the user inputted
            p = float(p)
            try:
                v = float(v)
                try:
                    n = float(n)
                    try:
                        t = float(t)
                        await ctx.send("```Can't calculate if all the values are already provided```")
                    except ValueError:  # need to calculate for temp
                        t = (p*v)/(r*n)
                        await ctx.send(f"```Temperature: {round(t, 3)}K```")
                except ValueError:  # calculate n
                    try:
                        t = float(t)
                        n = (p*v)/(r*t)
                        await ctx.send(f"```Moles: {round(n, 3)} mol```")
                    except ValueError:
                        await ctx.send("```Invalid command format | +calculate help```")
            except ValueError:
                try:
                    n = float(n)
                    t = float(t)
                    v = (n*r*t)/p
                    await ctx.send(f"```Volume: {round(v, 3)}L```")
                except ValueError:
                    await ctx.send("```Invalid command format | +calculate help```")
        except ValueError:
            try:
                v = float(v)
                n = float(n)
                t = float(t)
                p = (n*r*t)/v
                await ctx.send(f"```Pressure: {round(p, 3)}kPa```")
            except ValueError:
                await ctx.send("```Invalid command format | +calculate help```")

    elif subcmd.lower().startswith('m'):  # molar mass calculation (takes only the first argument)
        try:
            formula, result = molar_mass(args[0])
        except IndexError:
            await ctx.send("```Invalid command format | +calculate help```")
            return
        formula = ''.join(formula)
        if not formula:  # could not read formula
            await ctx.send(f"```Invalid formula given: {args[0]} (Formulas are case-sensitive)```")
        else:
            formula = convert_subscript(formula)
            await ctx.send(f"```Molar mass of {formula}: {result} g/mol```")

    elif subcmd.lower().startswith('s'):
        # solution based from https://medium.com/swlh/balancing-chemical-equations-with-python-837518c9075b
        pass
    else:
        await ctx.send("```Invalid command format | +calculate help```")


@Bot.command(name='balance', aliases=["b", 'bal'])
async def balance_equation(ctx, *arg):
    output = balance(''.join(arg))  # spaces don't actually change output this way
    await ctx.send(f"```Balanced equation: {''.join(output)}```")


# subroutines
# processing (input and outputs are async commands listen earlier)
def transpose(matrix):
    # transpose 'matrix' (sympy can do this too, but I would rather stay with standard library as much as possible
    rows = len(matrix)
    columns = len(matrix[0])

    new_matrix = []
    for j in range(columns):
        row = []
        for i in range(rows):
            row.append(matrix[i][j])
        new_matrix.append(row)
    return new_matrix


def balance(equation):  # very verbose comments (since I don't fully understand it)

    equation = equation.split('=')
    reactants = equation[0].split('+')
    products = equation[1].split('+')  # get reactants and products in separate lists

    for i in range(len(reactants)):  # puts terms into matrix
        add_matrix(reactants[i], i, 1)
    for i in range(len(products)):
        add_matrix(products[i], i + len(reactants), -1)  # product quantities are negative

    # must use sympy (or numpy i think) to find null space
    # I guess this function can't be marked for alberta curriculum project?
    # (trying to reduce amount of modules used but no idea how to do this otherwise)
    answer = Matrix(transpose(CoefficientMatrix)).nullspace()[0]  # take the first item in transposed null space matrix
    denominators = []
    for i in answer:
        print(type(i))
        denominators.append(i.q)  # add denominators of each coefficient to find lcm
        # .q means denominator in (p/q), since values in answers are actually sympy objects
    multiple = lcm(denominators)
    answer = answer * multiple   # multiply matrix by lcm
    coeff = answer.tolist()  # turns matrix to array

    output = []
    for i in range(len(reactants)):
        if coeff[i][0] != 1:
            output.append(str(coeff[i][0]))  # add number if coefficient is not 1
        else:
            output.append('')  # add blank string if coefficient is  1
        output.append(convert_subscript(reactants[i]))  # add string of corresponding reactant
        if i + 1 < len(reactants):  # if there are more reactants
            output.append(" + ")

    output.append(" -> ")

    for i in range(len(products)):
        if coeff[i + len(reactants)][0] != 1:
            output.append(str(coeff[i + len(reactants)][0]))
        else:
            output.append('')
        output.append(convert_subscript(products[i]))
        if i < len(products) - 1:
            output.append(" + ")

    CoefficientMatrix.clear()
    ElementList.clear()
    # clear global lists so they don't hold up memory, and to allow for reuse of functions
    return output


def add_matrix(compound, index, side):
    # need reg expressions to avoid typing a LOT of extra lines
    segments = re.split('(\([A-Za-z0-9]*\)[0-9])', compound)  # find anything surrounded by parenthesis
    # therefore does not support polyatomic decomposition reactions (which are beyond scope of high school chem)
    for segment in segments:
        if segment.startswith("("):
            segment = re.split('\)([0-9]*)', segment)  # find a ')' followed by a number of digits
            multiplier = int(segment[1])  # i.e. in (NO3)2 multiplier is 2
            segment = segment[0][1:]  # only get digits
        else:
            multiplier = 1  # blank means there is only 1 of the element

        parsed_list = re.split('([A-Z][a-z]?)', segment)
        # returns a list of of either element symbol or empty string/number in alternating order
        # empty string means 1, and first number/empty string is the coefficient of the entire reactant
        # CH4 becomes ['', 'C', '', 'H', '4']
        # find a element (capital followed by optional lower-case)
        # this means that elements don't need to be real, just a capital followed by optional lowercase letter

        i = 0
        while i < len(parsed_list) - 1:  # read the list of elements/numbers
            i += 1  # only increase by one if value is not zero (otherwise i should increment by 2)
            if len(parsed_list[i]) > 0:
                # element is not blank string
                if parsed_list[i + 1].isdigit():  # matches all coefficients which are not blank
                    amount = int(parsed_list[i + 1]) * multiplier  # take number and multiplier (element coefficient)
                    if index == len(CoefficientMatrix):
                        # if matrix needs new row (add row when index number is same as length of matrix), first element of each molecule will trigger this statement
                        # new row for each reactant / product
                        CoefficientMatrix.append([])
                        for iteration in ElementList:
                            CoefficientMatrix[index].append(0)  # fill row with zeros for each element in molecule
                    if parsed_list[i] not in ElementList:  # if the element was not already added
                        ElementList.append(parsed_list[i])  # add element to the list of elements (elements will be in same order so they can be put together)
                        for j in range(len(CoefficientMatrix)):
                            CoefficientMatrix[j].append(0)  # add zero to every row in matrix for each new element

                    col = ElementList.index(parsed_list[i])  # find index number of element in the element list
                    CoefficientMatrix[index][col] = amount * side  # side is 1 for reactants is -1 for products
                    # replaces the zero with an actual number (amount of that element)
                    i += 1  # add extra 1 to i to get to the next number in list (skip the elements)

                else:  # blank just means 1 (code is still the same as above
                    amount = 1
                    if index == len(CoefficientMatrix):
                        CoefficientMatrix.append([])
                        for iteration in ElementList:
                            CoefficientMatrix[index].append(0)
                    if parsed_list[i] not in ElementList:
                        ElementList.append(parsed_list[i])
                        for j in range(len(CoefficientMatrix)):
                            CoefficientMatrix[j].append(0)
                    col = ElementList.index(parsed_list[i])
                    CoefficientMatrix[index][col] = amount * side

def gcd(a, b):  # euclidean algorithm
    if a == 0:
        return b
    return gcd(b % a, a)


def balance_ionic(pos_ion, neg_ion):
    global CURSOR
    # get charge from database
    charge1 = CURSOR.execute("SELECT charge FROM elements WHERE symbol = ?", [pos_ion]).fetchone()
    if charge1 is None:
        charge1 = CURSOR.execute("SELECT charge FROM ions WHERE formula = ?", [pos_ion]).fetchone()

    charge2 = CURSOR.execute("SELECT charge FROM elements WHERE symbol = ?", [neg_ion]).fetchone()
    if charge2 is None:
        charge2 = CURSOR.execute("SELECT charge FROM ions WHERE formula = ?", [neg_ion]).fetchone()
    if charge1 is not None and charge2 is not None:
        charge2 = charge2[0][0]  # take most common ionic charge
        charge1 = charge1[0][0]
        if charge1.isnumeric() and charge2.isnumeric():
            charge1 = int(charge1)
            charge2 = int(charge2)
            divisor = gcd(charge1, charge2)
            charge1 = charge1 // divisor
            charge2 = charge2 // divisor

            coeff1 = charge2
            coeff2 = charge1

            if not coeff1 == 1:
                for i in pos_ion:
                    if i.isnumeric():
                        pos_ion = f"({pos_ion})"
                        break
            else:
                coeff1 = ''
            if not coeff2 == 1:
                for i in neg_ion:
                    if i.isnumeric():
                        neg_ion = f"({neg_ion})"
                        break
            else:
                coeff2 = ''
            formula = f"{pos_ion}{coeff1}{neg_ion}{coeff2}"
            return convert_subscript(formula)
        else:
            return False
    else:
        return False


def test_soluble(pos_ion, neg_ion):
    # uses same logic as precipitate calculator, but without storing anything in memory for the rest of the program
    # exceptions
    if (pos_ion, neg_ion) in (("Co", "IO3"), ("Fe", "OOCCOO")):
        return True
    elif (pos_ion, neg_ion) in (("Rb", "ClO4"), ("Cs", "ClO4"), ("Ag", "CH3COO"), ("Hg2", "CH3COO")):
        return False

    elif neg_ion == "F":  # row 2 of solubility table
        if pos_ion in ("Li", "Mg", "Ca", "Sr", "Ba", "Fe", "Hg2", "Pb"):
            return False
        else:
            return True
    elif neg_ion in ("Cl", "Br", "I"):  # row 3
        if pos_ion in ("Cu", "Ag", "Hg2", "Pb", "Tl"):
            return False
        else:
            return True
    elif neg_ion == "SO4":  # row 4
        if pos_ion in ("Ca", "Sr", "Ba", "Ag", "Hg2", "Pb", "Ra"):
            return False
        else:
            return True
    elif pos_ion in ("Li", "Na", "K", "Rb", "Cs", "Fr", "NH4") or neg_ion in ("ClO3", "ClO4", "NO3", "CH3COO"):
        # row 1 of table (has to come after row 2 due to LiF being exception to the rule)
        return True
    else:  # row 5-7 (every other possible case where the compound is soluble has been covered)
        return False


# add and delete from database
def add_ion(name, formula, charge):
    name = name.capitalize()
    formula, mass = molar_mass(formula)
    if not formula:  # if molar_mass returned False (formula invalid)
        return False
    formula = ''.join(formula)
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
    file.close()
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
    CURSOR.execute('''
        CREATE TABLE 
            ions(name TEXT NOT NULL, formula PRIMARY KEY, charge INTEGER NOT NULL, molar_mass TEXT NOT NULL);''')

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
