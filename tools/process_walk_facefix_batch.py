#!/usr/bin/env python3
from pathlib import Path
from collections import deque
import subprocess, json
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'work' / 'walk_facefix_raw'
OUT = ROOT / 'work' / 'walk_facefix_processed'
VIDEOS = ROOT / 'previews' / 'videos' / 'walk-facefix'
CONTACTS = ROOT / 'previews' / 'contact-sheets' / 'walk-facefix'
FRAMES = ROOT / 'previews' / 'frames' / 'walk-facefix-v1'
for p in (OUT, VIDEOS, CONTACTS, FRAMES): p.mkdir(parents=True, exist_ok=True)
CHARS = [
    ('securitocat','Securitocat'),
    ('octoliberty','OctoLiberty'),
    ('codercat','Codercat'),
    ('dinotocat','Dinotocat'),
    ('jetpacktocat','Jetpacktocat'),
    ('pythocat','Pythocat'),
    ('octobiwan','Octobiwan'),
    ('labtocat','Labtocat'),
]
COLS=4; ROWS=2

def font(size=24,bold=False):
    for p in ['/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf','/System/Library/Fonts/Supplemental/Helvetica.ttf','/System/Library/Fonts/SFNS.ttf']:
        try: return ImageFont.truetype(p,size)
        except Exception: pass
    return ImageFont.load_default()
FONT=font(26,True); SMALL=font(17,False)

def keep(img,min_area=700):
    arr=np.array(img.convert('RGBA')); alpha=arr[...,3]>10; h,w=alpha.shape; seen=np.zeros((h,w),bool); comps=[]
    for yy in range(h):
        for sx in np.where(alpha[yy]&~seen[yy])[0]:
            if seen[yy,sx] or not alpha[yy,sx]: continue
            q=deque([(yy,int(sx))]); pts=[]; seen[yy,sx]=1
            while q:
                y,x=q.popleft(); pts.append((y,x))
                for ny,nx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                    if 0<=ny<h and 0<=nx<w and alpha[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx]=1; q.append((ny,nx))
            ys,xs=zip(*pts); comps.append((len(pts),(min(xs),min(ys),max(xs)+1,max(ys)+1),pts))
    if not comps: return Image.fromarray(arr.astype(np.uint8),'RGBA')
    largest=max(c[0] for c in comps); mask=np.zeros((h,w),bool)
    for area,bbox,pts in comps:
        x0,y0,x1,y1=bbox; bw=x1-x0; bh=y1-y0
        if area==largest or (area>=max(min_area,int(largest*.018)) and bw>=16 and bh>=16):
            yy,xx=zip(*pts); mask[yy,xx]=1
    arr[...,3]=np.where(mask,arr[...,3],0)
    return Image.fromarray(arr.astype(np.uint8),'RGBA')

def remove_bg(cell):
    arr=np.array(cell.convert('RGBA')); rgb=arr[...,:3].astype(np.int16); h,w=rgb.shape[:2]; e=max(12,min(h,w)//20)
    samples=np.concatenate([rgb[:e,:].reshape(-1,3),rgb[h-e:,:].reshape(-1,3),rgb[:,:e].reshape(-1,3),rgb[:,w-e:].reshape(-1,3)])
    bg=np.median(samples,axis=0); dist=np.sqrt(((rgb-bg)**2).sum(axis=2)); base=dist<45
    bgmask=np.zeros((h,w),bool); q=deque()
    for x in range(w):
        if base[0,x]: q.append((0,x))
        if base[h-1,x]: q.append((h-1,x))
    for y in range(h):
        if base[y,0]: q.append((y,0))
        if base[y,w-1]: q.append((y,w-1))
    while q:
        y,x=q.popleft()
        if bgmask[y,x] or not base[y,x]: continue
        bgmask[y,x]=1
        if y>0: q.append((y-1,x))
        if y<h-1: q.append((y+1,x))
        if x>0: q.append((y,x-1))
        if x<w-1: q.append((y,x+1))
    m=bgmask.copy()
    for _ in range(2):
        n=m.copy(); n[:-1,:]|=m[1:,:]; n[1:,:]|=m[:-1,:]; n[:,:-1]|=m[:,1:]; n[:,1:]|=m[:,:-1]
        m=n&(dist<78)
    arr[...,3]=np.where(m,0,arr[...,3])
    return keep(Image.fromarray(arr.astype(np.uint8),'RGBA'))

def process(name):
    raw=Image.open(RAW/f'{name}_walk_raw.png').convert('RGBA')
    W,H=raw.size; cw,ch=W//COLS,H//ROWS; sprites=[]
    for idx in range(8):
        cell=raw.crop(((idx%4)*cw,(idx//4)*ch,(idx%4+1)*cw,(idx//4+1)*ch))
        clean=remove_bg(cell); bbox=clean.getbbox()
        sprites.append(clean.crop(bbox) if bbox else clean)
    maxw=max(s.width for s in sprites); maxh=max(s.height for s in sprites)
    fw=max(560,maxw+150); fh=max(760,maxh+160)
    rights=[]
    for spr in sprites:
        c=Image.new('RGBA',(fw,fh),(0,0,0,0))
        c.alpha_composite(spr,((fw-spr.width)//2,fh-spr.height-58))
        rights.append(c)
    lefts=[ImageOps.mirror(f) for f in rights]
    sheet=Image.new('RGBA',(fw*8,fh*2),(0,0,0,0))
    for i,f in enumerate(rights): sheet.alpha_composite(f,(i*fw,0))
    for i,f in enumerate(lefts): sheet.alpha_composite(f,(i*fw,fh))
    sheet_path=OUT/f'{name}_walk_right_left_facefix_v1.png'
    sheet.save(sheet_path)
    # contact
    check=Image.new('RGB',(fw*4,fh*2),(232,232,232)); d=ImageDraw.Draw(check)
    for yy in range(0,fh*2,32):
        for xx in range(0,fw*4,32):
            if (xx//32+yy//32)%2: d.rectangle((xx,yy,xx+31,yy+31),fill=(206,206,206))
    contact=check.convert('RGBA')
    for i,f in enumerate(rights): contact.alpha_composite(f,((i%4)*fw,(i//4)*fh))
    contact.convert('RGB').save(CONTACTS/f'{name}_walk_facefix_v1_contact.jpg',quality=92)
    print(name, 'canvas', fw, fh, 'sprites', [s.size for s in sprites])
    return rights, sheet_path

def panel_bg(w,h,label,accent,n):
    im=Image.new('RGB',(w,h),(15,19,29)).convert('RGBA'); d=ImageDraw.Draw(im,'RGBA')
    for gy in range(12,h,34):
        for gx in range(10,w,34):
            if ((gx//34+gy//34+n//5)%8)==0: d.rounded_rectangle((gx,gy,gx+15,gy+15),radius=4,fill=accent+(38,))
    ground=int(h*.80); d.rectangle((0,ground,w,h),fill=(38,47,58,255))
    for x in range(-h,w,44): d.line((x,ground,x+int(h*.22),h),fill=(55,67,80,150),width=1)
    d.rounded_rectangle((16,14,min(w-16,36+len(label)*12),50),radius=10,fill=(5,9,18,220),outline=accent+(165,),width=1)
    d.text((28,22),label,font=SMALL,fill=(242,246,252))
    return im,ground

processed={name:process(name)[0] for name,_ in CHARS}
for p in FRAMES.glob('*.png'): p.unlink()
W,H=1920,1080; panelW,panelH=W//4,H//2
positions=[(i*panelW,j*panelH) for j in range(2) for i in range(4)]
colors=[(88,166,255),(163,113,247),(255,171,112),(63,185,80),(121,192,255),(126,231,135),(210,168,255),(248,81,73)]
N=96
for n in range(N):
    canvas=Image.new('RGB',(W,H),(5,9,18)).convert('RGBA')
    for idx,(name,label) in enumerate(CHARS):
        x0,y0=positions[idx]; panel,ground=panel_bg(panelW,panelH,label,colors[idx],n)
        f=processed[name][n%8]
        scale=min(.47,275/f.height,315/f.width)
        spr=f.resize((int(f.width*scale),int(f.height*scale)),Image.Resampling.LANCZOS)
        if n < N//2:
            x=42+int(n*(panelW-180)/(N//2-1))
        else:
            x=panelW-122-int((n-N//2)*(panelW-180)/(N//2-1))
            spr=ImageOps.mirror(spr)
        y=ground-spr.height
        alpha=np.array(spr)[...,3]; ys,xs=np.where(alpha>10)
        if len(xs):
            sh_w=max(1,int((xs.max()-xs.min()+1)*.68)); sh_h=16
            shadow=Image.new('RGBA',(sh_w,sh_h),(0,0,0,0)); sd=ImageDraw.Draw(shadow,'RGBA')
            sd.ellipse((0,0,sh_w-1,sh_h-1),fill=(0,0,0,105)); shadow=shadow.filter(ImageFilter.GaussianBlur(3))
            panel.alpha_composite(shadow,(x+spr.width//2-sh_w//2,ground-sh_h//2))
        panel.alpha_composite(spr,(x,y)); canvas.alpha_composite(panel,(x0,y0))
    canvas.convert('RGB').save(FRAMES/f'{n:04d}.png')
video=VIDEOS/'octodex_walk_facefix_batch_v1.mp4'
subprocess.run(['ffmpeg','-y','-framerate','12','-i',str(FRAMES/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
# combined contact
contact=Image.new('RGB',(4096,1640),(20,20,25)); d=ImageDraw.Draw(contact)
cellW,cellH=240,360
for idx,(name,label) in enumerate(CHARS):
    gx=(idx%4)*1024; gy=(idx//4)*820; d.text((gx+18,gy+14),label,font=FONT,fill=(255,255,255))
    for j,f in enumerate(processed[name]):
        scale=min(.31,185/f.height,205/f.width)
        spr=f.resize((max(1,int(f.width*scale)),max(1,int(f.height*scale))),Image.Resampling.LANCZOS)
        bg=Image.new('RGB',(cellW,cellH),(230,230,230)).convert('RGBA'); bd=ImageDraw.Draw(bg)
        for yy in range(0,cellH,24):
            for xx in range(0,cellW,24):
                if (xx//24+yy//24)%2: bd.rectangle((xx,yy,xx+23,yy+23),fill=(204,204,204))
        ground=315; bd.line((0,ground,cellW,ground),fill=(90,90,90),width=2); bg.alpha_composite(spr,((cellW-spr.width)//2,ground-spr.height))
        contact.paste(bg.convert('RGB'),(gx+18+(j%4)*(cellW+8),gy+48+(j//4)*(cellH+8)))
contact_path=CONTACTS/'octodex_walk_facefix_batch_v1_contact.jpg'; contact.save(contact_path,quality=90)
print('VIDEO',video)
print('CONTACT',contact_path)
