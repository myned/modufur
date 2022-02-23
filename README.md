# Modufur
An experimental [Hikari](https://www.hikari-py.dev) Discord bot for reverse image searching using [SauceNAO](https://saucenao.com) & [Kheina](https://kheina.com)
## Prerequisites
A Unix-based operating system is used for the following commands\
[WSL](https://docs.microsoft.com/en-us/windows/wsl) can be used to run Linux on Windows, but is not required to run the bot
## Requirements
[Git](https://git-scm.com/downloads)\
[Python](https://www.python.org) 3.10+\
[Poetry](https://python-poetry.org)
## Installing
Clone this repository
```
git clone https://github.com/Myned/Modufur.git
```
Go to the project folder
```
cd Modufur
```
Create a virtual environment and install dependencies
```
poetry install
```
## Usage
Go to the project folder
```
cd Modufur
```
Run with optimizations
```
poetry run python -OO run.py
```
## Setup
Run to create `config.toml`\
The file will automatically generate if it does not exist
```
guilds = [] # guild IDs to register commands, empty for global
client = 0 # bot application ID
token = "" # bot token
activity = "" # bot status
saucenao = "" # saucenao token
e621 = "" # e621 token
```
## Updating
Go to the project folder
```
cd Modufur
```
Pull changes from the repository
```
git pull
```
Remove the virtual environment folder (necessary because of git dependencies)
```
rm -rf .venv
```
Reinstall and update the virtual environment
```
poetry update
```
## Uninstalling
Remove the project folder
```
rm -rf Modufur
```
## Contributing
1. [Fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo) this repository on GitHub
2. Make changes to the code
3. Format the code with [Black](https://black.readthedocs.io/en/stable) inside the project folder
    ```
    poetry run python black .
    ```
4. [Commit](https://github.com/git-guides/git-commit) the changes to the fork
5. Create a [pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request) from the fork
## FAQ
### What happened to the public bot?
My Discord account was deleted, so a new bot had to be created.
### Why not link to the public bot here?
Although public, I do not wish for it to be excessively used due to API quotas.
### Why can't I send explicit images to the bot?
Discord currently has no way to disable scanning content for bots.\
You can send links uploaded elsewhere instead.
## Credits
[hikari](https://github.com/hikari-py/hikari)\
[hikari-lightbulb](https://github.com/tandemdude/hikari-lightbulb)\
[hikari-miru](https://github.com/HyperGH/hikari-miru)\
[pysaucenao](https://github.com/FujiMakoto/pysaucenao)
