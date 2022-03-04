import hikari
import lightbulb
import songbird
from songbird import hikari as songkari
from youtubesearchpython import __future__ as youtube

import config as c
from tools import components


plugin = lightbulb.Plugin("music", include_datastore=True)
plugin.add_checks(lightbulb.guild_only)
plugin.d.queue = {}


# Subclass string to store metadata in coroutine parameters
# Prevents needing to query for metadata again
class Metadata(str):
    def __new__(cls, url, **_):
        return super().__new__(cls, url)

    def __init__(self, _, *, title, thumbnail, duration):
        self.title = title
        self.thumbnail = thumbnail
        self.duration = duration


# Check if command is used in music channel
@lightbulb.Check
def music_channel(context):
    if str(context.guild_id) not in c.config.get("music", {}):
        return True

    return context.channel_id == c.config.get("music", {}).get(str(context.guild_id), None)


# Check if user is in bot voice channel
@lightbulb.Check
def voice_only(context):
    voice = context.bot.cache.get_voice_state(context.guild_id, context.user.id)

    if not voice:
        return False
    if (
        context.guild_id in context.bot.voice.connections
        and voice.channel_id != context.bot.voice.connections[context.guild_id].channel_id
    ):
        return False

    return True


# Listener for music exceptions
@plugin.set_error_handler()
async def on_error(event):
    error = None

    match event.exception.__cause__ or event.exception:
        case AttributeError():
            error = f"***Queue may still be initializing.** If this continues, please notify my master, {event.context.bot.application.owner.mention}*"
        case lightbulb.MissingRequiredPermission():
            error = "***You are missing required permissions***"
        case lightbulb.CheckFailure():
            if "voice_only" in str(event.exception):
                error = "***Join the voice channel first***"
            elif "music_channel" in str(event.exception):
                error = f"***Command must be used in <#{c.config['music'][str(event.context.guild_id)]}>***"

    if error:
        await event.context.respond(error, flags=hikari.MessageFlag.EPHEMERAL)

        return True


# Send notification to music channel on track fail
# async def on_fail(driver, source):
#     for guild_id in c.config["music"]:
#         if driver is plugin.d.queue[int(guild_id)].driver:
#             await plugin.bot.rest.create_message(c.config["music"][guild_id], "***Track is unplayable, skipping***")
#             break


# # Send notification to music channel on next track
# def on_next(driver, track_handle):
#     for guild_id in c.config["music"]:
#         if driver is plugin.d.queue[int(guild_id)].driver:
#             plugin.bot.create_task(_on_next(guild_id, track_handle))
#             break


# # Awaitable required
# async def _on_next(guild_id, track_handle):
#     await plugin.bot.rest.create_message(
#         c.config["music"][guild_id],
#         (
#             hikari.Embed(
#                 title=track_handle.metadata.title,
#                 url=track_handle.metadata.source_url,
#                 color=(await plugin.bot.rest.fetch_guild(int(guild_id))).get_my_member().get_top_role().color,
#             )
#             .set_thumbnail(track_handle.metadata.thumbnail)
#             .set_footer(convert(round(track_handle.metadata.duration)))
#         ),
#     )


@plugin.command
@lightbulb.add_checks(lightbulb.has_guild_permissions(hikari.Permissions.MANAGE_GUILD))
@lightbulb.option("channel", "Channel for music commands, empty to unset", hikari.GuildChannel, required=False)
@lightbulb.command("set", "Settings for the server, Manage Server permission required", ephemeral=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def set(context):
    if context.options.channel:
        c.config.setdefault("music", {})[str(context.guild_id)] = int(context.options.channel.id)
    else:
        if str(context.guild_id) in c.config.get("music", {}):
            del c.config["music"][str(context.guild_id)]
        if "music" in c.config and not c.config["music"]:
            del c.config["music"]

    c.dump()

    if str(context.guild_id) in c.config.get("music", {}):
        await context.respond(f"**Music channel set to <#{c.config['music'][str(context.guild_id)]}>**")
    else:
        await context.respond("**Music channel unset**")


@plugin.command
@lightbulb.add_checks(music_channel)
@lightbulb.command("move", "Move to a voice channel, queue intact")
@lightbulb.implements(lightbulb.SlashCommand)
async def move(context):
    if not context.bot.cache.get_voice_state(context.guild_id, context.user.id):
        await context.respond("***Join a voice channel first***", flags=hikari.MessageFlag.EPHEMERAL)
        return

    driver = await connect(context)

    await context.respond(f"**Connected to <#{driver.channel_id}>**")


@plugin.command
@lightbulb.add_checks(voice_only, music_channel)
@lightbulb.option("query", "Search for a track, playlist, or link to play", required=False)
@lightbulb.command("play", "Play or resume music from YouTube")
@lightbulb.implements(lightbulb.SlashCommand)
async def play(context):
    if not context.options.query:
        if not await running(context.guild_id):
            await context.respond("***Nothing to resume***", flags=hikari.MessageFlag.EPHEMERAL)
            return
        if (await plugin.d.queue[context.guild_id].track_handle.get_info()).playing == songbird.PlayMode.Play:
            await context.respond("***Already playing***", flags=hikari.MessageFlag.EPHEMERAL)
            return

        plugin.d.queue[context.guild_id].track_handle.play()

        await context.respond("**Resuming**")
        return

    await context.respond(hikari.ResponseType.DEFERRED_MESSAGE_CREATE)

    # Search using youtube-search-python instead of songbird-py
    search = await youtube.Search(context.options.query, limit=5).next()
    embed = hikari.Embed(color=context.get_guild().get_my_member().get_top_role().color).set_author(name="Now playing")
    sources = []
    match = None

    # Filter only videos or playlists
    for result in search["result"]:
        match result["type"]:
            case "video":
                match = result
                embed.set_footer(result["duration"])

                sources.append(
                    songbird.ytdl(
                        Metadata(
                            result["link"],
                            title=result["title"],
                            thumbnail=result["thumbnails"][0]["url"],
                            duration=result["duration"],
                        )
                    )
                )
                break
            case "playlist":
                match = result
                embed.set_footer(f"{result['videoCount']} tracks")
                playlist = youtube.Playlist(result["link"])

                while playlist.hasMoreVideos:
                    await playlist.getNextVideos()
                for video in playlist.videos:
                    sources.append(
                        songbird.ytdl(
                            Metadata(
                                video["link"],
                                title=video["title"],
                                thumbnail=video["thumbnails"][0]["url"],
                                duration=video["duration"],
                            )
                        )
                    )
                break

    if not match:
        await context.respond(
            "***Couldn't find many results.** Try a more specific query*", flags=hikari.MessageFlag.EPHEMERAL
        )
        return

    if context.guild_id not in context.bot.voice.connections:
        await connect(context)

    embed.title = match["title"]
    embed.url = match["link"]
    embed.set_thumbnail(match["thumbnails"][0]["url"])

    if await running(context.guild_id):
        plugin.d.queue[context.guild_id].extend(sources)

        if len(sources) > 1:
            embed.set_author(
                name=f"Positions {plugin.d.queue[context.guild_id].index(sources[0]) + 1}-{plugin.d.queue[context.guild_id].index(sources[-1]) + 1} in queue"
            )
        else:
            match plugin.d.queue[context.guild_id].index(sources[0]):
                case 0:
                    embed.set_author(name="Next in queue")
                case _ as index:
                    embed.set_author(name=f"Position {index + 1} in queue")
    else:
        plugin.d.queue[context.guild_id].extend(sources)

    await context.respond(embed)


@plugin.command
@lightbulb.add_checks(voice_only, music_channel)
@lightbulb.option("position", "Position of the track to skip to", required=False, autocomplete=True)
@lightbulb.command("skip", "Skip the current or to a specific track")
@lightbulb.implements(lightbulb.SlashCommand)
async def skip(context):
    if not await running(context.guild_id):
        await context.respond("***Nothing to skip***", flags=hikari.MessageFlag.EPHEMERAL)
        return
    if len(plugin.d.queue[context.guild_id]) == 0:
        plugin.d.queue[context.guild_id].skip()

        await context.respond("**Last track skipped**")
        return

    embed = (
        hikari.Embed(
            title=plugin.d.queue[context.guild_id][0].cr_frame.f_locals["url"].title,
            url=plugin.d.queue[context.guild_id][0].cr_frame.f_locals["url"],
            color=context.get_guild().get_my_member().get_top_role().color,
        )
        .set_author(name="Skipped to")
        .set_thumbnail(plugin.d.queue[context.guild_id][0].cr_frame.f_locals["url"].thumbnail)
        .set_footer(plugin.d.queue[context.guild_id][0].cr_frame.f_locals["url"].duration)
    )

    # Reconstruct queue in lieu of an index skip
    if context.options.position:
        position = context.options.position.split()[0]

        if not position.isdigit() or int(position) not in range(1, len(plugin.d.queue[context.guild_id]) + 1):
            await context.respond("***Invalid position***", flags=hikari.MessageFlag.EPHEMERAL)
            return

        sources = plugin.d.queue[context.guild_id][int(position) - 1 :]

        plugin.d.queue[context.guild_id].track_handle.stop()
        plugin.d.queue[context.guild_id].clear()
        plugin.d.queue[context.guild_id] = songbird.Queue(plugin.d.queue[context.guild_id].driver)
        plugin.d.queue[context.guild_id].extend(sources)

        embed.title = plugin.d.queue[context.guild_id][0].cr_frame.f_locals["url"].title
        embed.url = plugin.d.queue[context.guild_id][0].cr_frame.f_locals["url"]
        embed.set_thumbnail(plugin.d.queue[context.guild_id][0].cr_frame.f_locals["url"].thumbnail)
        embed.set_footer(plugin.d.queue[context.guild_id][0].cr_frame.f_locals["url"].duration)
    else:
        plugin.d.queue[context.guild_id].skip()

    await context.respond(embed)


@plugin.command
@lightbulb.add_checks(voice_only, music_channel)
@lightbulb.option("position", "Position of the track to remove", autocomplete=True)
@lightbulb.command("remove", "Remove a track from the queue")
@lightbulb.implements(lightbulb.SlashCommand)
async def remove(context):
    # Build embeds for paginator
    def build(_, content):
        return (
            hikari.Embed(
                description=content,
                color=context.get_guild().get_my_member().get_top_role().color,
            )
            .set_author(name="Removed")
            .set_footer(f"{len(sources)} track{'s' if len(sources) > 1 else ''}")
        )

    if not await running(context.guild_id):
        await context.respond("***Nothing to remove***", flags=hikari.MessageFlag.EPHEMERAL)
        return

    split = context.options.position.split()

    # Determine if range is used
    if "-" in split[0]:
        positions = "".join(split[0]).split("-")
    else:
        positions = [split[0] for _ in range(2)]

    # Check if input is valid and within range
    if not all(position.isdigit() for position in positions) or not all(
        int(position) in range(1, len(plugin.d.queue[context.guild_id]) + 1) for position in positions
    ):
        await context.respond("***Invalid position***", flags=hikari.MessageFlag.EPHEMERAL)
        return

    # Remove sources from starting index multiple times
    sources = [
        plugin.d.queue[context.guild_id].pop(int(positions[0]) - 1)
        for _ in range(int(positions[0]), int(positions[1]) + 1)
    ]

    # Build paginator
    paginator = lightbulb.utils.EmbedPaginator()
    paginator.set_embed_factory(build)
    for position, source in enumerate(sources, start=int(positions[0])):
        paginator.add_line(
            f"**{position}** · {source.cr_frame.f_locals['url'].duration} · [{truncate(source.cr_frame.f_locals['url'].title)}]({source.cr_frame.f_locals['url']})"
        )

    pages = [page for page in paginator.build_pages()]

    if len(pages) > 1:
        selector = components.Selector(
            pages=pages,
            buttons=[components.Back(), components.Forward()],
            timeout=600,
        )

        await selector.send(context.interaction, ephemeral=True)
    else:
        await context.respond(pages[0])


# Autocomplete songs from queue
@skip.autocomplete("position")
@remove.autocomplete("position")
async def position_autocomplete(option, interaction):
    if not await running(interaction.guild_id):
        return

    suggestions = []

    if "-" in option.value:
        split = option.value.split("-")

        if not all(value.isdigit() for value in split):
            return

        for index, source in enumerate(plugin.d.queue[interaction.guild_id], start=1):
            if index in range(int(split[0]), int(split[1]) + 1):
                suggestions.append(
                    f"{split[0]}-{split[1]} · {index} · {truncate(source.cr_frame.f_locals['url'].title)}"
                )
    else:
        for index, source in enumerate(plugin.d.queue[interaction.guild_id], start=1):
            if not option.value or option.value in str(index):
                suggestions.append(f"{index} · {truncate(source.cr_frame.f_locals['url'].title)}")

    return suggestions[:25]


@plugin.command
@lightbulb.add_checks(voice_only, music_channel)
@lightbulb.command("pause", "Pause the current track")
@lightbulb.implements(lightbulb.SlashCommand)
async def pause(context):
    if not await running(context.guild_id):
        await context.respond("***Nothing to pause***", flags=hikari.MessageFlag.EPHEMERAL)
        return
    if (await plugin.d.queue[context.guild_id].track_handle.get_info()).playing == songbird.PlayMode.Pause:
        await context.respond("***Already paused***", flags=hikari.MessageFlag.EPHEMERAL)
        return

    plugin.d.queue[context.guild_id].track_handle.pause()

    await context.respond("**Paused**")


@plugin.command
@lightbulb.add_checks(voice_only, music_channel)
@lightbulb.command("stop", "Stop the current track and clear the queue")
@lightbulb.implements(lightbulb.SlashCommand)
async def stop(context):
    if context.guild_id not in plugin.d.queue:
        await context.respond("***Nothing to stop***", flags=hikari.MessageFlag.EPHEMERAL)
        return

    try:
        if (
            plugin.d.queue[context.guild_id].track_handle
            and await plugin.d.queue[context.guild_id].track_handle.get_info()
        ):
            plugin.d.queue[context.guild_id].track_handle.stop()
    except songbird.SongbirdError:
        pass

    plugin.d.queue.clear()

    if context.guild_id in context.bot.voice.connections:
        await context.bot.voice.disconnect(context.guild_id)

    await context.respond("**Stopped**")


@plugin.command
@lightbulb.add_checks()
@lightbulb.command("nowplaying", "Show the current track", ephemeral=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def nowplaying(context):
    if not await running(context.guild_id):
        await context.respond("***Nothing is playing***", flags=hikari.MessageFlag.EPHEMERAL)
        return

    state = await plugin.d.queue[context.guild_id].track_handle.get_info()

    await context.respond(
        hikari.Embed(
            title=plugin.d.queue[context.guild_id].track_handle.metadata.title,
            url=plugin.d.queue[context.guild_id].track_handle.metadata.source_url,
            color=context.get_guild().get_my_member().get_top_role().color,
        )
        .set_author(name="Now playing")
        .set_thumbnail(plugin.d.queue[context.guild_id].track_handle.metadata.thumbnail)
        .set_footer(
            f"{convert(round(state.position))} / {convert(round(plugin.d.queue[context.guild_id].track_handle.metadata.duration))}"
        )
    )


@plugin.command
@lightbulb.add_checks()
@lightbulb.command("queue", "List songs in the queue", ephemeral=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def queue(context):
    # Build embeds for paginator
    def build(_, content):
        return (
            hikari.Embed(
                title=plugin.d.queue[context.guild_id].track_handle.metadata.title,
                url=plugin.d.queue[context.guild_id].track_handle.metadata.source_url,
                description=content,
                color=context.get_guild().get_my_member().get_top_role().color,
            )
            .set_author(name="Queue")
            .set_thumbnail(plugin.d.queue[context.guild_id].track_handle.metadata.thumbnail)
            .set_footer(
                f"{len(plugin.d.queue[context.guild_id]) + 1} track{'s' if len(plugin.d.queue[context.guild_id]) > 1 else ''}"
            )
        )

    if not await running(context.guild_id):
        await context.respond("***Nothing in the queue***", flags=hikari.MessageFlag.EPHEMERAL)
        return

    # Build paginator
    paginator = lightbulb.utils.EmbedPaginator()
    paginator.set_embed_factory(build)
    for index, source in enumerate(plugin.d.queue[context.guild_id], start=1):
        paginator.add_line(
            f"**{index}** · {source.cr_frame.f_locals['url'].duration} · [{truncate(source.cr_frame.f_locals['url'].title)}]({source.cr_frame.f_locals['url']})"
        )

    pages = [page for page in paginator.build_pages()]

    if len(pages) > 1:
        selector = components.Selector(
            pages=pages,
            buttons=[components.Back(), components.Forward()],
            timeout=600,
        )

        await selector.send(context.interaction, ephemeral=True)
    else:
        await context.respond(pages[0])


# (Re)connect to voice channel and restart queue
async def connect(context):
    voice = context.bot.cache.get_voice_state(context.guild_id, context.user.id)

    if context.guild_id in context.bot.voice.connections:
        await context.bot.voice.disconnect(context.guild_id)

    driver = await context.bot.voice.connect_to(
        context.guild_id,
        voice.channel_id,
        songkari.Voicebox,
        deaf=True,
    )

    # Reconstruct queue
    if await running(context.guild_id):
        sources = [songbird.ytdl(plugin.d.queue[context.guild_id].track_handle.metadata.source_url)] + plugin.d.queue[
            context.guild_id
        ]

        await plugin.d.queue[context.guild_id].clear()
        plugin.d.queue[context.guild_id] = songbird.Queue(driver)
        plugin.d.queue[context.guild_id].extend(sources)
    elif context.guild_id not in plugin.d.queue:
        plugin.d.queue[context.guild_id] = songbird.Queue(driver)

    return driver


# Return True if queue exists and is playing
async def running(guild_id):
    try:
        return (
            guild_id in plugin.d.queue
            and plugin.d.queue[guild_id].track_handle
            and await plugin.d.queue[guild_id].track_handle.get_info()
        )
    # TrackError is not exposed, so use base songbird error
    except songbird.SongbirdError:
        return False


# Convert seconds into (HH:)MM:SS
def convert(seconds):
    h = seconds // 3600
    m = seconds % 3600 // 60
    s = seconds % 3600 % 60  # YouTube values seem to be one second lower

    return f"{f'{h}:' if h else ''}{m}:{s:02d}"


# Truncate if characters are longer than limit
# Discord does not handle escaped markdown syntax correctly, so remove []
def truncate(string, limit=80):
    string = string.replace("[", "").replace("]", "")

    return f"{string[:limit]}..." if len(string) > limit else string


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.create_task(bot.voice.disconnect_all())
    bot.remove_plugin(plugin)
