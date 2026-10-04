import json,re
def hafo_grams(name):
    """all mass/volume quantities in a hafo row name, in g or ml"""
    n=(name or '').lower().replace(',', '.')
    out=[]
    for num,unit in re.findall(r'(\d+(?:\.\d+)?)\s*(կգ|կգր|kg|кг|գր|գ|g|гр|г|մլ|ml|мл|լ|l|л)(?![a-zա-ֆа-я])', n):
        x=float(num)
        if unit in ('կգ','կգր','kg','кг','լ','l','л'): x*=1000
        out.append(round(x,1))
    return out
def ours(rec):
    s=rec.get('size') or {}
    if s.get('measureType') in ('mass','volume'):
        return round(s['netContent']/1000,1), round(s['itemContent']/1000,1), s.get('packCount')
    return None
