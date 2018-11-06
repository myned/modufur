def tostring(i, *, order=None, newline=False):
    o = ''
    if i:
        for v in i:
            o += v + (' ' if newline is False else '\n')
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


def dict_tostring(i, f=True, newline=False):
    o = ''

    if f:
        if i:
            for k, v in i.items():
                o += '**' + k + ':** `' + tostring(v) + '`\n'
    elif newline is True:
        if i:
            for k, v in i.items():
                o += k + ': ```' + tostring(v, newline=newline) + '```\n'
    else:
        if i:
            for k, v in i.items():
                o += k + ': ```' + tostring(v) + '```\n'
    return o


def dictelem_tostring(i):
    o = ''
    if i:
        for dic, elem in i.items():
            o += '**__' + dic + '__**\n'
            for k, v in elem.items():
                o += '***' + k + ':*** `' + tostring(v) + '`\n'
    return o
