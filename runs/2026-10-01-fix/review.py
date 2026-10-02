import json,os,sys
from PIL import Image,ImageDraw,ImageFont
H=os.path.dirname(os.path.abspath(__file__)); g=sys.argv[1]
R=json.load(open(f'{H}/cand/{g}/'+('result-review.json' if g=='A' else 'result.json')+''))
P={}
for f in os.listdir(H+'/snapshot'):
    d=json.load(open(f'{H}/snapshot/{f}')); P[d['id']]=d
V={v['id']:(p,v) for p in P.values() for v in p['variants']}
F=ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf",15); T=220
rows=[r for r in R if r.get('status')=='found']
for n in range(0,len(rows),8):
    ch=rows[n:n+8]
    sh=Image.new('RGB',(190+4*(T+8),len(ch)*(T+26)),'white'); d=ImageDraw.Draw(sh)
    for i,r in enumerate(ch):
        p,v=V[r['variant']]; y=i*(T+26)
        d.multiline_text((4,y+4),f"V{v['id']} {v['size_label']}\n{p['name'][:22]}\n{v['name'][:22]}\nCURRENT →",fill='black',font=F)
        cur=f"{H}/img/{v['images'][0]}.jpg"
        ims=[cur]+[f if os.path.isabs(f) else os.path.join(H,'cand',g,os.path.basename(f)) for f in r['files'][:3]]
        for j,f in enumerate(ims):
            try: im=Image.open(f).convert('RGB'); w,h=im.size; im.thumbnail((T,T)); sh.paste(im,(190+j*(T+8),y)); d.text((190+j*(T+8),y+T+3),('current' if j==0 else f'cand {j}')+f' {w}x{h}',fill='red',font=F)
            except Exception as e: d.text((190+j*(T+8),y+20),'ERR '+os.path.basename(f),fill='red',font=F)
    sh.save(f'{H}/sheets/review-{g}-{n//8}.png')
print(len(rows))
