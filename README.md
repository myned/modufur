# Modufur
An experimental [Hikari](https://www.hikari-py.dev) Discord bot for reverse image searching using [SauceNAO](https://saucenao.com) & [Kheina](https://kheina.com).
## Requirements
[Python](https://www.python.org) 3.10+\
[Poetry](https://python-poetry.org)
## Installing
```
git clone -b hikari https://github.com/Myned/Modufur.git
```
```
cd Modufur
```
```
poetry install
```
## Usage
```
poetry run python run.py
```
## Setup
`config.toml` will automatically generate if it does not exist
```
guilds = [] # guild IDs to register commands, empty for global
client = 0 # bot application ID
token = "" # bot token
activity = "" # bot status
saucenao = "" # saucenao token
e621 = "" # e621 token
```
## Updating
```
cd Modufur
```
```
git pull
```
```
poetry env remove python
```
```
poetry update
```
## Credits
[hikari](https://github.com/hikari-py/hikari)\
[hikari-lightbulb](https://github.com/tandemdude/hikari-lightbulb)\
[hikari-miru](https://github.com/HyperGH/hikari-miru)\
[pysaucenao](https://github.com/FujiMakoto/pysaucenao)
