## CSE2910-project

### How to use:

1. Create Discord bot account, or click on this link to invite a pre-created bot account to a guild/server:
   https://discord.com/api/oauth2/authorize?client_id=856918934674735114&permissions=2148006976&scope=bot
   If choosing to use direct message, the bot will need to share a mutual server with you first in order to message.
   

2. If using a different bot account, replace the variable TOKEN with the bot token as a string, otherwise, the current
   TOKEN value should also connect to a bot account. (CSE2910-BOT#9444).
   Token should be kept secure or else the bot account could be used by other people.
   

3. Install the libraries discord.py (mandatory) and sympy (optional, but more complicated balancing functions require it):
Since all libraries are registered to PyPI,
   
    On Windows, use the commands:

    `py -3 -m pip install discord.py | py -3 -m pip install sympy`

    On Linux or Mac:

    `python3 -m pip install -U discord.py | python3 -m pip install sympy.`

    (Sympy has dependency on mpmath library which may need to be installed too: [py -3/python3] -m pip install mpmath)
   

4. Run code, and hope nothing goes wrong (because then I lose marks).