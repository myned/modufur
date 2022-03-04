import os

import hikari
import lightbulb
import miru

import config as c


# Unix optimizations
# https://github.com/hikari-py/hikari#uvloop
if os.name != "nt":
    import uvloop

    uvloop.install()

bot = lightbulb.BotApp(
    token=c.config["token"],
    default_enabled_guilds=c.config["guilds"],
    help_slash_command=False,
)


# Listener for global command exceptions
@bot.listen(lightbulb.CommandErrorEvent)
async def on_error(event):
    error = c.ERROR

    match event.exception.__cause__ or event.exception:
        case lightbulb.BotMissingRequiredPermission():
            error = f"***Missing required permissions: `{event.exception.missing_perms}`***"
        case lightbulb.MissingRequiredPermission():
            error = f"***You are missing required permissions: `{event.exception.missing_perms}`***"
        case hikari.ForbiddenError():
            raise event.exception
        case _:
            await bot.application.owner.send(c.error(event))

    try:
        await event.context.respond(error, flags=hikari.MessageFlag.EPHEMERAL)
    except:
        await event.context.interaction.edit_initial_response(error, components=None)

    raise event.exception


miru.load(bot)
bot.load_extensions_from("tools", "commands")
bot.run(activity=hikari.Activity(name=c.config["activity"], type=c.ACTIVITY) if c.config["activity"] else None)
