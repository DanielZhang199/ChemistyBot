'''
title: Discord chemistry bot
author: Daniel Zhang
data-created: 2021-06-11
'''
# standard library (os module is only used to environmental variables)
import pathlib
import sqlite3
import re

# required dependency | py -m pip install discord.py  (for windows)
import discord
from discord.ext import commands

# optional dependency for equation balancing | py -m pip install sympy
try:
    from sympy import Matrix, lcm
except ModuleNotFoundError:
    print("Dependencies required to preform equation balancing were not found, stoichometric functions will be unavailable")

Bot = commands.Bot(command_prefix='+', help_command=None)
# change bot command prefix to '+' and create custom help command

DATABASE = 'project.db'
PERIODIC_TABLE = 'periodic_table.csv'  # taken from chemistry data booklet
POLYATOMIC_IONS = 'polyatomic_ions.csv'

# discord markdown has no subscript formatting option
Subscript = {"1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉", "0": "₀", }
Anti_Subscript = {i: j for j, i in Subscript.items()}

# Lists used as global/memory variables for balancing/stoich
CoefficientMatrix = []  # matrix of the number of each element of an unbalanced equation
ElementList = []  # names of element for each matrix row
LoadedEquation = []  # this will just be a list in a list to send data between functions
EquationCoeff = []  # stores the coefficient, then name of molecule (for easier stoich calculation code)


# coroutines (I already know the flowchart is going to be a mess)


@Bot.event
async def on_ready():  # when bot connects
    await Bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name='your every command | +help')
    )
    print(f"{Bot.user} is online")


@Bot.event
async def on_disconnect():  # when bot disconnects
    print(f"{Bot.user} has disconnected")


@Bot.event
async def on_command_error(ctx, error):  # when error (invalid command) is raised
    await ctx.send(f"```Error: {str(error)} | type +help for list of commands```")

# inputs/outputs  (commands)


@Bot.command(name='help', aliases=['h', 'commands'])  # custom help command
async def help_message(ctx):  # bot commands pass context (ctx) parameter always, and will crash if coroutine does not accept at least one parameter
    # ctx contains the message object, as well as lets you reply directly with ctx.send('Message')
    embed = discord.Embed(title="CSE2910 Chemistry Bot",
                          description='''Bot that helps with chemistry and whilst taking up my processor power and RAM.                    
\nCredit to Mohammad-Ali Bandzar for equation balancing code:
\n(Bandzar, M.-A. (2020, May 27). Balancing Chemical Equations With Python. Medium. https://medium.com/swlh/balancing-chemical-equations-with-python-837518c9075b.)''',
                          color=5935975)
    embed.add_field(name="Element/Ion Database",
                    value='''```
+database (Element / Ion) (symbol): Gets element/ion data
+database add (ion name) (ion formula) (charge)
+database delete (ion name, * to reset databases)```''',
                    inline=False)
    embed.add_field(name="Balance Equation | +balance help",
                    value='''```+balance (equation): \nBalances equations```''',
                    inline=False)
    embed.add_field(name="Unit Conversion | +convert help",
                    value='```+convert (value) (conversion): \nConverts one unit to another```',
                    inline=False)
    embed.add_field(name="Ionic Compound Formation",
                    value='```+ionic (pos ion) (neg ion): \nBalances and determines solubility (most common charge)```',
                    inline=False)
    embed.add_field(name="Calculations | +calculate help for more info",
                    value='''```
+calculate gas (p) (v) (n) (t)
+calculate moles (formula)```''',
                    inline=False)
    embed.add_field(name="Stoichiometry | +stoich help for more info",
                    value='''```
+stoich load (equation)
+stoich show
+stoich calculate (id) (unit) (value) (id2) (unit2)```''',
                    inline=False)
    await ctx.send(embed=embed)


@Bot.command(name='hello')  # say hello back
async def hello(ctx):
    message = await ctx.send(f"Hello! {ctx.author.mention}")
    await message.add_reaction('\N{THUMBS UP SIGN}')


@Bot.command(name='database', aliases=['data', 'dat', 'd'])  # reading, writing, deleting from database
# aliases are just alternate names for command (+database and +data will run the same command)
async def output_database(ctx, subcmd='', arg1=None, arg2=None, arg3=None):  # takes context, subcommand, and 3 arguements
    # variables are given default values of 'None' so that error messages can be displayed
    # subcmd, arg1-3 are all arguments (the first 4 words user types after command), and have default values
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
        try:  # in case of row error
            success = add_ion(arg1, arg2, arg3)  # success is the outcome of write command
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
    if value.isnumeric():  # is integer
        decimal_places = 1
    else:
        try:
            decimal_places = len(value.split('.')[1])
            value = float(value)
        except ValueError:
            await ctx.send("```Conversion value must be a number. | +convert help```")
            return
        except IndexError:
            await ctx.send("```Conversion value must be a number. | +convert help```")
            return

    if conversion.lower() == 'c-k':  # C>K
        await ctx.send(f"```{value}°C = {round(value + 273.15, decimal_places)}K```")
    elif conversion.lower() == 'k-c':  # K>C
        await ctx.send(f"```{value}K = {round(value - 273.15, decimal_places)}°C```")
    elif conversion.lower() == 'kpa-atm':
        await ctx.send(f"```{value}kPa = {round(value / 101.325, decimal_places)}Atm```")
    elif conversion.lower() == 'atm-kpa':
        await ctx.send(f"```{value}Atm = {round(value * 101.325, decimal_places)}kPa```")
    elif conversion.lower() == 'kpa-mmhg':
        await ctx.send(f"```{value}kPa = {round(value * 7.50062, decimal_places)}mmHg```")
    elif conversion.lower() == 'mmhg-kpa':
        await ctx.send(f"```{value}mmHg = {round(value / 7.50062, decimal_places)}kPa```")
    elif conversion.lower() == 'mmhg-atm':
        await ctx.send(f"```{value}mmHg = {round(value / 760, decimal_places)}Atm```")
    elif conversion.lower() == 'atm-mmhg':
        await ctx.send(f"```{value}Atm = {round(value * 760, decimal_places)}mmHg```")
    else:
        await ctx.send(f"```Could not find requested conversion | +convert help to show list of conversions```")


@Bot.command(name='ionic', aliases=["soluble", 'sol', 'ion', 'i'])
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

        embed.add_field(name="Molar Mass | +calculate moles (formula)",
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
        r = 8.314  # gas constant for units used
        try:  # lots of error checking to figure out what the user inputted
            # this is defnitely not good code, but I'm not sure how else to test for floats
            p = float(p)
            try:
                v = float(v)
                try:
                    n = float(n)
                    try:  # user inputted all values of gas law (so theres nothing to calculate for)
                        t = float(t)
                        await ctx.send("```Can't calculate if all the values are already provided```")
                    except ValueError:  # calculate for t ans p, v, and n are floats and t is not
                        t = (p*v)/(r*n)
                        await ctx.send(f"```Temperature: {round(t, 5)}K```")
                except ValueError:  # calculate n, as p and v are float and n is not float
                    try:
                        t = float(t)
                        n = (p*v)/(r*t)
                        await ctx.send(f"```Moles: {round(n, 5)} mol```")
                    except ValueError:
                        await ctx.send("```Invalid command format | +calculate help```")
            except ValueError:  # calculating for v as p is float and v is not float
                try:
                    n = float(n)
                    t = float(t)
                    v = (n*r*t)/p
                    await ctx.send(f"```Volume: {round(v, 5)}L```")
                except ValueError:
                    await ctx.send("```Invalid command format | +calculate help```")
        except ValueError:  # calculating for p as p is not float
            try:
                v = float(v)
                n = float(n)
                t = float(t)
                p = (n*r*t)/v
                await ctx.send(f"```Pressure: {round(p, 5)}kPa```")
            except ValueError:
                await ctx.send("```Invalid command format | +calculate help```")

    elif subcmd.lower().startswith('m'):  # molar mass calculation (takes only the first argument)
        try:
            result = molar_mass(args[0])
        except IndexError:
            await ctx.send("```Invalid command format | +calculate help```")
            return
        if not result:  # could not read formula
            await ctx.send(f"```Invalid formula given: {args[0]} (Formulas are case-sensitive)```")
        else:
            formula = convert_subscript(args[0])
            await ctx.send(f"```Molar mass of {formula}: {result} g/mol```")

    else:
        await ctx.send("```Invalid command format | +calculate help```")


@Bot.command(name='stoichiometry', aliases=["stoich", 'equation', 'e'])
async def stoich_commands(ctx, subcmd, *args):
    if subcmd.lower().startswith('h'):  # help
        embed = discord.Embed(title="Chemical Equations (Stoichiometry)", color=4905928)
        embed.add_field(name="Load equation | +stoich load (equation)",
                        value='''```
equation: unbalanced equation
i.e. +cal stoich load NO3 + Co = Co(NO3)2```''',
                        inline=False)
        embed.add_field(name="Load equation | +stoich show",
                        value='''```
Shows currently loaded equation```''',
                        inline=False)
        embed.add_field(name="Load equation | +stoich calculate (id) (unit) (value) (id2) (unit2)",
                        value='''```
Converts amount of one substance to another based on balanced equation:
id: id number of molecule
unit: grams or moles (default to moles)
value: number of grams or moles
id2: id number of molecule to calculate for

Example: +stoich cal 1 grams 20.3 3 grams```''',
                        inline=False)
        await ctx.send(embed=embed)

    if subcmd.lower().startswith("l"):  # load equation

        try:
            equation = balance(''.join(args))  # try to balance
        except IndexError:
            await ctx.send("```Invalid equation formatting | +balance help for details```")
            return
        except TypeError:  # this shouldn't ever happen unless theres an bug (or polyatomic decomposition maybe)
            await ctx.send("```Could not find a way to balance equation.```")
            return
        except NameError:  # means that prerequisite modules (sympy) were not installed
            await ctx.send("```Dependencies for balancing were not found, cannot preform stoich commands.```")
            return

        LoadedEquation.clear()
        EquationCoeff.clear()  # clear previously saved data (if applicable)
        LoadedEquation.append(equation)  # save equation to memory to display
        for i in equation:
            if not i.isdigit() and not i == '' and not i == ' + ' and not i == ' -> ':
                coefficient = equation[equation.index(i) - 1]
                if coefficient == '':
                    coefficient = 1
                else:
                    coefficient = int(coefficient)
                EquationCoeff.append([coefficient, convert_subscript(i, False)])
                # save elements and their coefficients for calculations
        await ctx.send("```Balanced equation loaded to memory.```")
        await ctx.send(embed=show_equation())

    elif subcmd.lower().startswith("s"):  # show loaded equation again
        if LoadedEquation:  # if list is not empty
            await ctx.send(embed=show_equation())
        else:
            await ctx.send("```Please load an equation first | +stoich load (equation)```")

    elif subcmd.lower().startswith("c"):  # calculate with mole ratio
        try:
            index = abs(int(args[0])) - 1  # don't want to deal with negative index numbers
            unit = args[1]
            value = float(args[2])
            output_index = abs(int(args[3])) - 1
            output_unit = args[4]
        except IndexError:
            await ctx.send("```Invalid command format | +stoich help```")
            return
        except ValueError:
            await ctx.send("```Invalid command format | +stoich help```")
            return
        if index < len(EquationCoeff) and output_index < len(EquationCoeff):
            ratio = EquationCoeff[output_index][0] / EquationCoeff[index][0]
            # mole ratio of requested molecule to given molecule

            if unit.lower().startswith('g'):  # if user inputted grams, convert to moles
                mole_mass = molar_mass(EquationCoeff[index][1])
                if mole_mass is None:
                    await ctx.send(f"```Could not find molar mass of molecule '{EquationCoeff[index][1]}'```")
                    return
                moles = value / mole_mass
            else:  # if given unit was moles
                moles = value

            moles = moles * ratio  # calculate moles of requested molecule, convert from moles
            output_molecule = convert_subscript(EquationCoeff[output_index][1])

            if output_unit.lower().startswith('g'):  # if user wants answer in grams
                mole_mass = molar_mass(EquationCoeff[output_index][1])
                # we can reuse variable names since they are no longer needed
                if mole_mass is None:
                    await ctx.send(f"```Could not find molar mass of molecule '{output_molecule}'```")
                    return
                await ctx.send(f"```The calculated mass of {output_molecule} is {round(moles * mole_mass, 5)} grams.```")
            else:
                await ctx.send(f"```The calculated quantity of {output_molecule} is {round(moles, 5)} moles.```")
    else:
        await ctx.send("```Invalid command format | +stoich help```")


@Bot.command(name='balance', aliases=["b", 'bal'])
async def balance_equation(ctx, *arg):
    if arg[0].lower() == 'help':  # user has to type out all of help since equations can also start with h
        embed = discord.Embed(title="Equation Balancing", color=4905928, description='''```
+balance (unbalanced equation):

i.e. +balance C6H12O6 + O2 = CO2 + H2O 

> Equation is case-sensitive
> Spaces between terms are technically optional
> Use '=' instead of '->'
> Only use brackets if they will be followed by coefficient
(i.e. NaNO3, instead of Na(NO3))```''')
        await ctx.send(embed=embed)
    else:
        try:
            output = balance(''.join(arg))  # join arguments so spaces don't actually change output this way
            if output is None:
                await ctx.send("```Could not find a way to balance equation```")
            else:
                await ctx.send(f"```Balanced equation: {''.join(output)}```")
        except IndexError:  # in theory all errors related to bad inputs are IndexErrors
            await ctx.send("```Invalid command format | +balance help```")
        except NameError:  # means that prerequisite modules (sympy) were not installed
            await ctx.send("```Dependencies for balancing were not found, cannot preform equation balancing.```")

# subroutines
# processing (input and outputs are mostly handled by the command systems


def transpose(matrix):
    # transpose 'matrix' (sympy can do this too, but I would rather stay with standard library as much as possible)
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
    CoefficientMatrix.clear()
    ElementList.clear()
    # in case there was error midway and function crashes
    equation = equation.split('=')

    # get reactants and products in separate lists (have to make sure there are multiple terms '+' first)
    reactants = equation[0].split('+')
    products = equation[1].split('+')

    # starting here this is NOT MY ORIGINAL CODE: credit to Mohammad-Ali Bandzar:
    # Bandzar, M.-A. (2020, May 27). Balancing Chemical Equations With Python. Medium. https://medium.com/swlh/balancing-chemical-equations-with-python-837518c9075b.
    for i in range(len(reactants)):  # puts terms into matrix
        add_matrix(reactants[i], i, 1)
    for i in range(len(products)):
        add_matrix(products[i], i + len(reactants), -1)  # product quantities are negative

    # must use sympy (or numpy i think) to find null space
    # I guess this function used for non-ib part of project(?)
    # Without dependencies, everything but balancing and stoich will still work so its not really a problem
    # (trying to reduce amount of modules used but no idea how to do this otherwise)
    try:
        answer = Matrix(transpose(CoefficientMatrix))  # converts to matrix object
        answer = answer.nullspace()[0]  # take the first item in transposed null space matrix  (sympy method)
    except IndexError:  # no answer was found (for whatever reason)
        CoefficientMatrix.clear()
        ElementList.clear()
        return None

    denominators = []  # get integer answers (since nullspace()[0] returns fractions)
    for i in answer:
        denominators.append(i.q)  # add denominators of each coefficient to find lcm
        # .q means denominator in (p/q), since values in answers are actually sympy objects
    multiple = lcm(denominators)
    answer = answer * multiple   # multiply matrix by lcm
    coeff = answer.tolist()  # turns matrix to array (sympy method)

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


def add_matrix(compound, row, side):  # also NOT MY CODE (works with previous code)
    # need reg expressions to parse user input without comparing to entire periodic table
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
                    if row == len(CoefficientMatrix):
                        # if matrix needs new row (add row when row number is same as length of matrix), first element of each molecule will trigger this statement
                        # new row for each reactant / product
                        CoefficientMatrix.append([])
                        for iteration in ElementList:
                            CoefficientMatrix[row].append(0)  # fill row with a blank value for each element in molecule (create columns)
                    if parsed_list[i] not in ElementList:  # if the element was not already added
                        ElementList.append(parsed_list[i])  # add element to the list of elements (elements will be in same order so they can be put together)
                        for j in range(len(CoefficientMatrix)):
                            CoefficientMatrix[j].append(0)

                    col = ElementList.index(parsed_list[i])  # find row number of element in the element list
                    CoefficientMatrix[row][col] += amount * side  # side is 1 for reactants is -1 for products
                    # replaces the zero with an actual number (amount of that element)
                    i += 1  # add extra 1 to i to get to the next number in list (skip the elements)

                else:  # blank just means 1 (code is still the same as above
                    amount = multiplier  # since the amount is 1, 1 * multiplier is = multiplier
                    if row == len(CoefficientMatrix):
                        CoefficientMatrix.append([])
                        for iteration in ElementList:
                            CoefficientMatrix[row].append(0)
                    if parsed_list[i] not in ElementList:
                        ElementList.append(parsed_list[i])
                        for j in range(len(CoefficientMatrix)):
                            CoefficientMatrix[j].append(0)
                    col = ElementList.index(parsed_list[i])
                    CoefficientMatrix[row][col] += amount * side

# everything after this is my code again


def gcd(a, b):  # i guess this was technically invented by euclid
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
        # as long as we have charges for both (this could crash if user added charges are invalid)
        charge2 = charge2[0][0]  # take most common (first) ionic charge
        charge1 = charge1[0][0]
        if charge1.isnumeric() and charge2.isnumeric():
            charge1 = int(charge1)
            charge2 = int(charge2)
            divisor = gcd(charge1, charge2)
            charge1 = charge1 // divisor
            charge2 = charge2 // divisor

            coeff1, coeff2 = charge2, charge1  # charges are really charges anymore, but rather just inverted coeff

            if not coeff1 == 1:  # need brackets for polyatomic ions
                if len(pos_ion) > 2 or len(pos_ion) == 2 and pos_ion.isupper():  # if longer than 2 or has 2 capitals (2 elements)
                    pos_ion = f"({pos_ion})"
                else:  # or theres a number in the ion formula
                    for i in pos_ion:
                        if i.isnumeric():
                            pos_ion = f"({pos_ion})"
                            break
            else:
                coeff1 = ''
            if not coeff2 == 1:  # need brackets for polyatomic ions
                if len(neg_ion) > 2 or len(neg_ion) == 2 and neg_ion.isupper():  # if longer than 2 or has 2 capitals (2 elements)
                    neg_ion = f"({neg_ion})"
                else:  # or theres a number in the ion formula
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
    mass = molar_mass(formula)
    if not mass:  # if molar_mass returned False (formula invalid)
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


def load_elements(table):
    file = open(table)
    content = file.readlines()
    file.close()
    content.pop(0)  # delete table header
    for i in range(len(content)):
        content[i] = content[i].split(',')
        content[i][-1] = content[i][-1][:-1]  # split each row into 2D array and remove new line (\n)
    print("Initializing element database")
    CURSOR.execute(''' CREATE TABLE elements(
    name TEXT NOT NULL, symbol TEXT NOT NULL, atomic_number INTEGER PRIMARY KEY, charge TEXT,
    molar_mass TEXT NOT NULL, group_name TEXT NOT NULL, electronegativity REAL, state TEXT NOT NULL);''')
    # while all molar masses are REAL values, they are stored as strings to keep significant figures when viewing

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
        content[i][3] = molar_mass(content[i][1])
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
    global CURSOR
    total = 0
    i = 0
    while i < len(formula):  # each letter can be upper case, lower case or a number
        coeff = None
        element = None

        if formula[i] == '(':  # this code was added later to calculate for all polyatomic ionic compounds
            # basically it just calculates the molar mass of formula inside brackets with this function (recursive)
            # then multiplies it by the coefficient at the end
            j = i + 1
            while formula[j] != ')':
                j += 1
            mass = float(molar_mass(formula[i + 1:j]))
            k = j + 1
            while formula[k].isnumeric():
                if k + 1 < len(formula):
                    k += 1
                else:
                    k += 1
                    break
            coeff = int(formula[j + 1:k])
            total += mass * coeff
            i = k - 1  # since we need to skip brackets, can't use for loop for i

        elif formula[i].isupper():  # the letter is capital (start of new element)
            try:  # we don't know if there are any more letters in the string
                if formula[i + 1].islower():  # the letter after is lowercase (two letter elements)
                    element = formula[i:(i + 2)]
                    try:
                        if formula[i + 2].isnumeric():  # check if next number is coefficient
                            j = i + 2
                            while formula[j].isnumeric():
                                # check how many consecutive digits there are
                                if j + 1 < len(formula):
                                    j = j + 1
                                else:
                                    j = j + 1
                                    break
                            coeff = int(formula[i + 2:j])
                    except IndexError:
                        pass
                elif formula[i + 1].isnumeric():  # same thing as before just if the element is only one letter long
                    j = i + 1
                    while formula[j].isnumeric():
                        if j + 1 < len(formula):
                            j = j + 1
                        else:
                            j = j + 1
                            break
                    coeff = int(formula[i + 1:j])
                    element = formula[i]
                elif formula[i + 1].isupper():  # next element, no coefficient
                    element = formula[i]
            except IndexError:
                element = formula[i]

            if coeff is None:
                coeff = 1

            # search element database for mass
            mass = CURSOR.execute("SELECT molar_mass FROM elements WHERE symbol = ?", [element]).fetchone()
            if mass is None:
                return False  # return that the formula is invalid
            mass = mass[0]
            if mass.startswith('('):  # if mass is in brackets
                mass = mass[1:-1]
            total = total + (float(mass) * int(coeff))

        i += 1

    return round(total, 2)  # does not use significant digits (not enough time to implement)

# outputs  (mostly just formatting and creating embeds)

def show_equation():   # display loaded equation
    embed = discord.Embed(title="Loaded Equation:",
                          description=''.join(LoadedEquation[0]),
                          color=4905928)
    molecule_list = ''
    for i in range(len(EquationCoeff)):
        molecule_list += f"{i+1}: {EquationCoeff[i][1]}\n"
    embed.add_field(name="Molecules",
                    value=molecule_list,
                    inline=False)  # displays element name
    return embed


def convert_subscript(text, direction=True):   # subscript for numbers; true means convert to, false convert from
    new_text = []
    if direction:
        for i in text:
            if i.isnumeric():
                i = Subscript[i]
            new_text.append(i)
        return ''.join(new_text)
    else:
        for i in text:  # Added in retrospect
            if i in Anti_Subscript:
                i = Anti_Subscript[i]
                new_text.append(i)
            else:
                new_text.append(i)
        return ''.join(new_text)


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
    TOKEN = 'ODU2OTE4OTM0Njc0NzM1MTE0.YNIB8g.u1FK2_qy7FuKkvoKximaXyCrxek'
    # If using this token, invite to a server with this link, (direct messaging should also work):
    # https://discord.com/api/oauth2/authorize?client_id=856918934674735114&permissions=2148006976&scope=bot
    if not (pathlib.Path.cwd() / DATABASE).exists():  # create tables
        CONNECTION = sqlite3.Connection(DATABASE)
        CURSOR = CONNECTION.cursor()
        load_elements(PERIODIC_TABLE)
        load_ions(POLYATOMIC_IONS)

    else:
        CONNECTION = sqlite3.Connection(DATABASE)
        CURSOR = CONNECTION.cursor()
    Bot.run(TOKEN)
    # starts main event loop
    # script will create discord session to bot matching token, then run code when command is activated
