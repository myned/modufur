import lightbulb


plugin = lightbulb.Plugin("help")


class Help(lightbulb.BaseHelpCommand):
    pass


def load(bot):
    bot.d.old_help_command = bot.help_command
    bot.help_command = Help(bot)


def unload(bot):
    bot.help_command = bot.d.old_help_command
    del bot.d.old_help_command
