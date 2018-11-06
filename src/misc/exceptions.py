from discord.ext.commands import errors as errext

base = '\N{WARNING SIGN} **An internal error has occurred.** This has been reported to my master. \N{WOLF FACE}'


async def send_error(ctx, error):
    await ctx.send('{}\n```\n{}```'.format(base, error))


# class NSFW(errext.CheckFailure):
#     pass

class Remove(Exception):
    pass

class SizeError(Exception):
    pass


class Wrong(Exception):
    pass


class Add(Exception):
    pass


class Execute(Exception):
    pass


class Evaluate(Exception):
    pass


class Left(Exception):
    pass


class Right(Exception):
    pass


class Save(Exception):
    def __init__(self, user=None, message=None):
        self.user = user
        self.message = message

class GoTo(Exception):
    pass


class Exists(errext.CommandError):
    pass


class MissingArgument(errext.CommandError):
    pass


class FavoritesNotFound(errext.CommandError):
    pass


class PostError(errext.CommandError):
    pass


class ImageError(errext.CommandError):
    pass


class MatchError(errext.CommandError):
    pass


class TagBlacklisted(errext.CommandError):
    pass


class BoundsError(errext.CommandError):
    pass


class TagBoundsError(errext.CommandError):
    pass


class TagExists(errext.CommandError):
    pass


class TagError(errext.CommandError):
    pass


class FlagError(errext.CommandError):
    pass


class BlacklistError(errext.CommandError):
    pass


class NotFound(errext.CommandError):
    pass


class Timeout(errext.CommandError):
    pass


class InvalidVideoFile(errext.CommandError):
    pass


class MissingAttachment(errext.CommandError):
    pass


class TooManyAttachments(errext.CommandError):
    pass


class CheckFail(errext.CommandError):
    pass


class Abort(Exception):
    def __init__(self, message=None):
        self.message = message


class Continue(Exception):
    pass
