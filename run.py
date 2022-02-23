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
    help_slash_command=True,
)


@bot.listen(lightbulb.CommandErrorEvent)
async def on_error(event):
    await bot.application.owner.send(c.error(event))

    try:
        await event.context.respond(c.ERROR)
    except:
        await event.context.interaction.edit_initial_response(c.ERROR, components=None)

    raise event.exception


miru.load(bot)
bot.load_extensions_from("tools", "commands")
bot.run(activity=hikari.Activity(name=c.config["activity"], type=c.ACTIVITY))
