import sqlite3

formula = 'Ce6He12Ox6'
CURSOR = sqlite3.Connection("project.db").cursor()
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

        # search element database for mass
        mass = CURSOR.execute("SELECT molar_mass FROM elements WHERE symbol = ?", [element]).fetchone()

        if coeff is None:
            coeff = 1
            parsed_formula.append(element)
        if coeff != 1:
            parsed_formula.append(element + str(coeff))
        print(element, coeff, mass)
    # if letter is not uppercase, skip the loop
print(parsed_formula)