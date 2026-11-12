"""Replace a Glovo product's images with one public image URL (tested 2026-11-10 on 11235S).

    python scripts/glovo-set-image.py <sku> <image_url> [--apply]     # needs openpyxl

`images` is a master-product field, so the call carries `original` (current state, as
glovo-titles.py does). Glovo downloads the URL and re-hosts it on glovo.dhmedia.io;
a 1200x1200 Siruk media URL worked. Dry run without --apply.
"""
import importlib.util, json, os, sys, time
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec=importlib.util.spec_from_file_location('gp',os.path.join(ROOT,'scripts','glovo-portal.py')); gp=importlib.util.module_from_spec(spec); spec.loader.exec_module(gp)
gp.TOKEN=gp.load_token()
sku,url=sys.argv[1],sys.argv[2]; apply='--apply' in sys.argv
q='''query($f:ProductFilter!,$p:PageInput!){products(filter:$f,page:$p){items{sku name price active imageUrls categoryIds maximumSalesQuantity internalId}}}'''
def get(loc):
    d=gp.gql(q,{'f':{'vendorIdentifier':gp.vendor(),'locale':loc,'searchTerm':sku,'active':None,'brandIds':[],'categoryIds':[]},'p':{'pageNumber':1,'pageSize':20}})['products']['items']
    return next(i for i in d if i['sku']==sku)
hy,en=get('hy_AM'),get('en_AM')
import openpyxl
desc=''
for r in openpyxl.load_workbook(gp.SHEET,read_only=True).worksheets[0].iter_rows(min_row=3,values_only=True):
    if r[0] is not None and str(r[0])==sku: desc=r[4] or ''
orig={'active':hy['active'],'categoryInternalIds':hy['categoryIds'],'descriptions':[{'locale':'hy_AM','value':desc}] if desc else [],
      'images':hy['imageUrls'] or [],'maximumSalesQuantity':hy['maximumSalesQuantity'] or 0,'price':hy['price'],'sku':sku,
      'titles':[{'locale':'hy_AM','value':hy['name']},{'locale':'en_AM','value':en['name']}]}
print(json.dumps({'sku':sku,'name_hy':hy['name'],'active':hy['active'],'images_now':hy['imageUrls'],'images_new':[url],'desc_found':bool(desc)},ensure_ascii=False,indent=1))
if not apply: print('DRY RUN'); sys.exit()
r=gp.gql('''mutation($u:ProductUpdate!){product(productUpdate:$u){active sku validationErrors{code message}}}''',
  {'u':{'sku':sku,'vendorIdentifier':gp.vendor(),'productInternalId':hy['internalId'],'images':[url],'original':orig}})
print(json.dumps(r,ensure_ascii=False))
time.sleep(5); print('after:',get('hy_AM')['imageUrls'])
