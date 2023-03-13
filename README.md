# Modufur
An experimental [Hikari](https://www.hikari-py.dev) Discord bot for reverse image searching using [SauceNAO](https://saucenao.com) & [Kheina](https://kheina.com)

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/B0B1AUB66)

## Prerequisites
Linux is used for the following commands\
[WSL](https://docs.microsoft.com/en-us/windows/wsl) can be used to run Linux on Windows, but is not required to run the bot
## Requirements
[Git](https://git-scm.com/downloads)\
[Python](https://www.python.org) 3.10+\
[Poetry](https://python-poetry.org/docs/master)
## Installing
1. Clone repository
```
git clone https://github.com/Myned/Modufur.git
```
2. Go to project folder
```
cd Modufur
```
3. Create a virtual environment and install dependencies
```
poetry install
```
## Usage
1. Go to project folder
```
cd Modufur
```
2. Run with optimizations
```
poetry run python -OO run.py
```
## Setup
Run to create `config.toml`\
The file will automatically generate if it does not exist
```
guilds = [] # guild IDs to register commands, empty for global
master = 0 # guild ID to register owner commands
client = 0 # bot application ID
token = "" # bot token
activity = "" # bot status
saucenao = "" # saucenao token
e621 = "" # e621 token
```
### systemd service
Run in the background on most Linux machines\
This assumes that the project folder is located at `~/.git/Modufur`\
Change the `WorkingDirectory` path in `modufur.service` if this is not the case
1. Go to project folder
```
cd Modufur
```
2. Copy user service file
```
cp modufur.service ~/.config/systemd/user
```
3. Replace `user` in `WorkingDirectory` with current user
```
sed -i "s|\(WorkingDirectory=/home/\)user|\1$(whoami)|" ~/.config/systemd/user/modufur.service
```
4. Reload user daemon
```
systemctl --user daemon-reload
```
5. Start and enable service on login
```
systemctl --user enable --now modufur
```
6. Enable lingering to start user services on boot
```
sudo loginctl enable-linger username
```
## Updating
1. Go to project folder
```
cd Modufur
```
2. Pull changes from repository
```
git pull
```
3. Update virtual environment
```
poetry update
```
4. Restart systemd user service
```
systemctl --user restart modufur
```
## Uninstalling
1. Stop and disable systemd user service
```
systemctl --user disable --now modufur
```
2. Remove systemd user service file
```
rm ~/.config/systemd/user/modufur.service
```
3. Optionally disable lingering
```
sudo loginctl disable-linger username
```
4. Remove project folder
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
[songbird-py](https://github.com/magpie-dev/Songbird-Py)\
[pysaucenao](https://github.com/FujiMakoto/pysaucenao)
