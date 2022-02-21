import urlextract
import hikari
import lightbulb
import pysaucenao

from tools import components, scraper


plugin = lightbulb.Plugin('booru')
extractor = urlextract.URLExtract()


@plugin.command
#@lightbulb.option('attachment', 'Attachment(s) to reverse', required=False)
@lightbulb.option('url', 'URL(s) to reverse, separated by space')
@lightbulb.command('reverse', 'Reverse image search using SauceNAO & Kheina', ephemeral=True)
@lightbulb.implements(lightbulb.SlashCommand, lightbulb.MessageCommand)
async def reverse(context):
    match context:
        case lightbulb.SlashContext():
            urls = extractor.find_urls(context.options.url or '', only_unique=True, with_schema_only=True)

            if not urls:
                await context.respond('**Invalid URL(s).**')
                return

            await _reverse(context, urls)
        case lightbulb.MessageContext():
            urls = extractor.find_urls(context.options.target.content or '', only_unique=True, with_schema_only=True)
            urls += [attachment.url for attachment in context.options.target.attachments if attachment.url not in urls]

            if not urls:
                await context.respond('**No images found.**')
                return

            selector = None

            if len(urls) > 1:
                selector = components.Selector(
                    pages=[f'**Select potential images to search: `{urls.index(url) + 1}/{len(urls)}`**\n{url}' for url in urls],
                    buttons=[components.Back(), components.Forward(), components.Select(), components.Confirm()],
                    urls=urls
                )

                await selector.send(context.interaction, ephemeral=True)
                await selector.wait()

                if selector.timed_out:
                    await context.interaction.edit_initial_response('**Timed out.**', components=None)
                    return

                urls = selector.selected

            await _reverse(context, urls, selector=selector)

@reverse.set_error_handler()
async def on_reverse_error(event):
    error = None

    match event.exception.__cause__:
        case pysaucenao.ShortLimitReachedException():
            error = '**API limit reached. Please try again in a minute.**'
        case pysaucenao.DailyLimitReachedException():
            error = '**Daily API limit reached. Please try again tomorrow.**'
        case pysaucenao.FileSizeLimitException() as url:
            error = f'**Image file size too large:**\n{url}'
        case pysaucenao.ImageSizeException() as url:
            error = f'**Image resolution too small:**\n{url}'
        case pysaucenao.InvalidImageException() as url:
            error = f'**Invalid image:**\n{url}'
        case pysaucenao.UnknownStatusCodeException():
            error = '**An unknown SauceNAO error has occurred. The service may be down.**'

    if error:
        try:
        await event.context.respond(error)
        except:
            await event.context.interaction.edit_initial_response(error, components=None)

        return True

async def _reverse(context, urls, *, selector=None):
    if not selector:
        await context.respond(hikari.ResponseType.DEFERRED_MESSAGE_CREATE)

    matches = await scraper.reverse(urls)

    if not matches:
        if selector:
            await context.interaction.edit_initial_response('**No matches found.**', components=None)
        else:
            await context.respond('**No matches found.**')
        return

    pages = [(hikari.Embed(
                title=match['artist'], url=match['source'], color=context.get_guild().get_my_member().get_top_role().color)
                .set_author(name=f'{match["similarity"]}% Match')
                .set_image(match['thumbnail'])
                .set_footer(match['index'])) if match else f'**No match found for:**\n{urls[index]}' for index, match in enumerate(matches)]

    if len(pages) > 1:
        selector = components.Selector(
            pages=pages,
            buttons=[components.Back(), components.Forward()],
            timeout=900
        )

        await selector.send_edit(context.interaction)
    else:
        if selector:
            await context.interaction.edit_initial_response(content=None, embed=pages[0], components=None)
        else:
            await context.respond(pages[0])

def load(bot):
    bot.add_plugin(plugin)
def unload(bot):
    bot.remove_plugin(plugin)
