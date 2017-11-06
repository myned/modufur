base = '\N{WARNING SIGN} **An internal error has occurred.** This has been reported to my master. \N{WOLF FACE}'


async def send_error(ctx, error):
    await ctx.send('{}\n```\n{}```'.format(base, error))


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
    pass


class GoTo(Exception):
    pass


class Exists(Exception):
    pass


class MissingArgument(Exception):
    pass


class FavoritesNotFound(Exception):
    pass


class PostError(Exception):
    pass


class ImageError(Exception):
    pass


class MatchError(Exception):
    pass


class TagBlacklisted(Exception):
    pass


class BoundsError(Exception):
    pass


class TagBoundsError(Exception):
    pass


class TagExists(Exception):
    pass


class TagError(Exception):
    pass


class FlagError(Exception):
    pass


class BlacklistError(Exception):
    pass


class NotFound(Exception):
    pass


class Timeout(Exception):
    pass


class InvalidVideoFile(Exception):
    pass


class MissingAttachment(Exception):
    pass


class TooManyAttachments(Exception):
    pass


class CheckFail(Exception):
    pass


class Abort(Exception):
    def __init__(self, message=None):
        self.message = message


class Continue(Exception):
    pass
