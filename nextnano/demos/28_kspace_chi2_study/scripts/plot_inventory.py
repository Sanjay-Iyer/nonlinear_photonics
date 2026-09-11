"""Build labeled QA contact sheets of all study PNGs; never edit source figures."""
from pathlib import Path
import json
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'outputs/plot_qa';out.mkdir(exist_ok=True)
files=sorted(p for p in (ROOT/'outputs').glob('28*/**/plots/*.png'))
inventory=[]
for start in range(0,len(files),6):
    page=Image.new('RGB',(1600,1110),'white');draw=ImageDraw.Draw(page)
    for j,p in enumerate(files[start:start+6]):
        im=Image.open(p).convert('RGB');inventory.append({'path':p.relative_to(ROOT).as_posix(),'size':im.size})
        im.thumbnail((790,330));x=(j%2)*800;y=(j//2)*370
        page.paste(im,(x,y+30));draw.text((x+5,y+5),p.name,fill='black')
    page.save(out/f'contact_{start//6+1:02d}.png')
(out/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
print(f'{len(files)} source plots; {(len(files)+5)//6} contact sheets in {out}')
