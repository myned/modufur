import os

import lightbulb


plugin = lightbulb.Plugin("master")


@plugin.command
@lightbulb.option("command", "What is your command, master?", required=False, choices=("reload", "sleep"))
@lightbulb.command("master", "Commands my master can demand of me", ephemeral=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def master(context):
    if context.user.id == context.bot.application.owner.id:
        match context.options.command:
            case "reload":
                context.bot.reload_extensions(*context.bot.extensions)

                extensions = [os.path.splitext(extension)[1][1:] for extension in context.bot.extensions]
                await context.respond(
                    f'**Reloaded `{"`, `".join(extensions[:-1])}`, and `{extensions[-1]}` for you, master.**'
                )
            case "sleep":
                await context.respond("**Goodnight, master.**")
                await context.bot.close()
            case _:
                await context.respond(f"**Hello, master.**")
    else:
        await context.respond(f"**{context.bot.application.owner.mention} is my master. 🐺**")


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
