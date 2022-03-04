import os

import lightbulb

import config as c


plugin = lightbulb.Plugin("master", default_enabled_guilds=c.config["master"])


@plugin.command
@lightbulb.option("command", "What is your command, master?", required=False, choices=("reload", "sleep", "invite"))
@lightbulb.command("master", "Commands my master can demand of me", ephemeral=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def master(context):
    if context.user.id == context.bot.application.owner.id:
        match context.options.command:
            case "reload":
                context.bot.reload_extensions(*context.bot.extensions)

                extensions = [os.path.splitext(extension)[1][1:] for extension in context.bot.extensions]
                await context.respond(
                    f"**Reloaded `{'`, `'.join(extensions[:-1])}`, and `{extensions[-1]}` for you, master**"
                )
            case "sleep":
                await context.respond("**Goodnight, master**")
                await context.bot.close()
            case "invite":
                await context.respond(
                    f"https://discord.com/api/oauth2/authorize?client_id={c.config['client']}&permissions=1024&scope=bot%20applications.commands"
                )
            case _:
                await context.respond(f"**Hello, master**")
    else:
        await context.respond(f"**{context.bot.application.owner.mention} is my master 🐺**")


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
