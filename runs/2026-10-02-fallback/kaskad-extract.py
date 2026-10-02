import re,sys,html,json
def ex(path):
    h=open(path,encoding='utf-8',errors='ignore').read()
    art=re.search(r'data-name="Артикул" data-value="([^"]+)',h)
    t=re.search(r'<h1[^>]*>([^<]+)',h)
    props=dict((html.unescape(re.sub('<[^>]+>','',a)).strip(),html.unescape(re.sub('<[^>]+>','',b)).strip()) for a,b in re.findall(r'<td class="char_name">(.*?)</td>\s*<td class="char_value">(.*?)</td>',h,re.S))
    if not props:
        props=dict((html.unescape(a).strip(),html.unescape(b).strip()) for a,b in re.findall(r'<span itemprop="name">([^<]+)</span>.*?<span itemprop="value">([^<]+)</span>',h,re.S))
    d=re.search(r'<div class="detail_text">(.*?)</div>',h,re.S) or re.search(r'itemprop="description"[^>]*>(.*?)</div>',h,re.S)
    imgs=sorted(set(re.findall(r'(/upload/iblock/[^"\' )]+\.(?:jpg|jpeg|png|webp))',h)))
    return {"article":art and art.group(1).strip(),"title":t and html.unescape(t.group(1)).strip(),"props":props,
            "desc":d and html.unescape(re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',d.group(1)))).strip(),"images":imgs[:12],
            "ean":re.findall(r'46\d{11}',h)[:3]}
for p in sys.argv[1:]: print(p, json.dumps(ex(p),ensure_ascii=False)[:1500]); print()
