# Modufur
An experimental [Hikari](https://github.com/hikari-py/hikari) Discord bot for reverse image searching using [SauceNAO](https://saucenao.com) & [Kheina](https://kheina.com)
## Requirements
[Python](https://www.python.org) 3.10+\
[Poetry](https://python-poetry.org)
## Installation
```
git clone https://github.com/Myned/Modufur.git
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
## Configuration
`config.toml`
```
guilds = [] # guild IDs to register commands, empty for global
client = 0 # bot application ID
token = "" # bot token
activity = "" # bot status
saucenao = "" # saucenao token
e621 = "" # e621 token
```
## Credits
[hikari](https://github.com/hikari-py/hikari)\
[hikari-lightbulb](https://github.com/tandemdude/hikari-lightbulb)\
[hikari-miru](https://github.com/HyperGH/hikari-miru)\
[pysaucenao](https://github.com/FujiMakoto/pysaucenao)
