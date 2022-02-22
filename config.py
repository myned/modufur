import toml
import hikari


ACTIVITY = hikari.ActivityType.LISTENING
ERROR = "```❗ An internal error has occurred. This has been reported to my master. 🐺```"
CONFIG = """\
guilds = [] # guild IDs to register commands, empty for global
client = 0 # bot application ID
token = "" # bot token
activity = "" # bot status
saucenao = "" # saucenao token
e621 = "" # e621 token
"""


try:
    config = toml.load("config.toml")
except FileNotFoundError:
    with open("config.toml", "w") as f:
        f.write(CONFIG)
        print("config.toml created with default values. Restart when modified.")
        exit()


def error(event):
    exception = event.exception.__cause__ or event.exception

    return (
        f"**`{event.context.command.name}` in {event.context.get_channel().mention if event.context.guild_id else 'DMs'}"
        f"```❗ {type(exception).__name__}: {exception}```**"
    )
