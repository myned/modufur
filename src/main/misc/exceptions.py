base = '‼️ **An internal error has occurred.** Please notify my master! 🐺'

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
class Continue(Exception):
    pass
