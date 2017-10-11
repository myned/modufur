import json

try:
    with open('background.json') as infile:
        background = json.load(infile)
        print('\"background.json\" loaded.')
except FileNotFoundError:
    with open('background.json', 'w+') as iofile:
        print('Background file not found: \"background.json\" created and loaded.')
        json.dump({}, iofile, indent=4, sort_keys=True)
        iofile.seek(0)
        background = json.load(iofile)

with open('config.json') as infile:
    config = json.load(infile)

def update(out, file):
    with open(file, 'w') as outfile:
        json.dump(out, outfile, indent=4, sort_keys=True)

import asyncio

async def clear(obj, interval=10*60, replace=None):
    if replace is None:
        if type(obj) is list:
            replace = []
        elif type(obj) is dict:
            replace = {}
        elif type(obj) is int:
            replace = 0
        elif type(obj) is str:
            replace = ''

    while True:
        obj = replace
        asyncio.sleep(interval)
