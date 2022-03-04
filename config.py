import toml
import hikari


# Hikari activity type
# https://www.hikari-py.dev/hikari/presences.html#hikari.presences.ActivityType
ACTIVITY = hikari.ActivityType.LISTENING
# Global command error response
ERROR = "```❗ An internal error has occurred. This has been reported to my master 🐺```"
# Local bot configuration
CONFIG = """\
guilds = [] # guild IDs to register commands, empty for global
master = 0 # guild ID to register owner commands
client = 0 # bot application ID
token = "" # bot token
activity = "" # bot status
saucenao = "" # saucenao token
e621 = "" # e621 token

"""


# Load or create config.toml
try:
    config = toml.load("config.toml")
except FileNotFoundError:
    with open("config.toml", "w") as f:
        f.write(CONFIG)
        print("config.toml created with default values. Restart when modified")
        exit()


# Global command error response for owner
def error(event):
    exception = event.exception.__cause__ or event.exception

    return (
        f"**`{event.context.command.name}` in {event.context.get_channel().mention if event.context.guild_id else 'DMs'}"
        f"```❗ {type(exception).__name__}: {exception}```**"
    )


# Write config to file
def dump():
    with open("config.toml", "w") as file:
        toml.dump(config, file)
