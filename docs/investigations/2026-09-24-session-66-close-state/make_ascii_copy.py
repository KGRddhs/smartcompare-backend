import collections, unicodedata, re, sys
base = r'C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/a47353ce-a0e3-4273-b85d-f21cfa01e031/scratchpad/'
src = base + sys.argv[1]
dst = base + sys.argv[2]
s = open(src, encoding='utf-8').read()
c = collections.Counter(ch for ch in s if ord(ch) > 127)
for ch, n in c.most_common():
    print(hex(ord(ch)), unicodedata.name(ch, '?'), n)
print('backslash-x seq:', len(re.findall(r'\\x[0-9a-fA-F]{2}', s)), 'backslash-u seq:', len(re.findall(r'\\u[0-9a-fA-F]{4}', s)))
m = {'\u2014': '-', '\u2013': '-', '\u2026': '...', '\u2192': '->', '\u2264': '<=', '\u2265': '>=', '\u00d7': 'x', '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2018': "'", '\u2022': '-', '\u00a0': ' '}
t = s
for a, b in m.items():
    t = t.replace(a, b)
rest = sorted(set(hex(ord(ch)) for ch in t if ord(ch) > 127))
print('remaining non-ascii after map:', rest)
t = t.encode('ascii', errors='replace').decode('ascii')
open(dst, 'w', encoding='ascii', newline='\n').write(t)
print('wrote', dst, len(t))
