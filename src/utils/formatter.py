from discord.ext.commands import Paginator


def tostring(i, *, order=None, newline=False):
    o = ''
    if i:
        for v in i:
            o += v + (' ' if newline is False else ' \n')
        o = o[:-1]
    elif order:
        o += order
    else:
        o = ' '
    return o


def tostring_commas(i):
    if i:
        o = ','
        for v in i:
            o += v + ','
        return o[:-1]
    return ''


async def paginate(
        ctx,
        i,
        start='',
        prefix='',
        kprefix='',
        ksuffix='\n',
        eprefix='```\n',
        ejoin=' ',
        esuffix='\n```',
        suffix='',
        end=''):
    paginator = Paginator(prefix=prefix, suffix=suffix)
    messages = []

    if start:
        paginator.add_line(start)

    if type(i) in (tuple, list, set):
        for e in sorted(i):
            if e and (e not in i) and (len(i) > 1):
                paginator.add_line(eprefix + f'{ejoin}'.join(e) + esuffix)
    elif type(i) is dict:
        for k, e in sorted(i.items()):
            if e and (k not in e) and (len(e) > 1):
                paginator.add_line(kprefix + k + ksuffix + eprefix + f'{ejoin}'.join(e) + esuffix)

    if end:
        paginator.add_line(end)

    for page in paginator.pages:
        messages.append(await ctx.send(page))

    return messages


def dictelem_tostring(i):
    o = ''
    if i:
        for dic, elem in i.items():
            o += '**__' + dic + '__**\n'
            for k, v in elem.items():
                o += '***' + k + ':*** `' + tostring(v) + '`\n'
    return o
