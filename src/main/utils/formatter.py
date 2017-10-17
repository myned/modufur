def tostring(i, *, random=False):
  o = ''
  if i:
    for v in i:
      o += v + ' '
    o = o[:-1]
  elif random is True:
    o += 'order:random'
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


def dict_tostring(i):
  o = ''
  if i:
    for k, v in i.items():
      o += '**' + k + ':** `' + tostring(v) + '`\n'
  return o


def dictelem_tostring(i):
  o = ''
  if i:
    for dic, elem in i.items():
      o += '**__' + dic + '__**\n'
      for k, v in elem.items():
        o += '***' + k + ':*** `' + tostring(v) + '`\n'
  return o
