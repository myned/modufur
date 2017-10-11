base = '⚠️ **An internal error has occurred.** Please notify my master! 🐺'

class Left(Exception): pass
class Right(Exception): pass
class Save(Exception): pass
class PostError(Exception): pass
class ImageError(Exception): pass
class MatchError(Exception): pass
class TagBlacklisted(Exception): pass
class BoundsError(Exception): pass
class TagBoundsError(Exception): pass
class TagExists(Exception): pass
class TagError(Exception): pass
class FlagError(Exception): pass
class BlacklistError(Exception): pass
class NotFound(Exception): pass
class Timeout(Exception): pass
class InvalidVideoFile(Exception): pass
class MissingAttachment(Exception): pass
class TooManyAttachments(Exception): pass
class CheckFail(Exception): pass
class Abort(Exception): pass
class Continue(Exception): pass
