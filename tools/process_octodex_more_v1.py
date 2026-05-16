from PIL import Image, ImageOps, ImageDraw
from pathlib import Path
import numpy as np, subprocess
from collections import deque
root=Path('/Users/jesusrubio/.openclaw/workspace/projects/octodex-sprites')
out=root/'out'
chars=['codercat','pythocat','octobiwan','labtocat','mona_classic_laptop']
labels={'codercat':'Codercat','pythocat':'Pythocat','octobiwan':'Octobiwan','labtocat':'Labtocat','mona_classic_laptop':'Mona classic: laptop aim'}
raw_files={
 'codercat':'codercat_walk_raw_v1.png',
 'pythocat':'pythocat_walk_raw_v1.png',
 'octobiwan':'octobiwan_walk_raw_v1.png',
 'labtocat':'labtocat_walk_raw_v1.png',
 'mona_classic_laptop':'mona_classic_laptop_raw_v1.png',
}
cols,rows=4,2
all_frames={}

def remove_gray_bg(cell):
    cell=cell.convert('RGBA')
    arr=np.array(cell)
    rgb=arr[...,:3].astype(np.int16); h,w=arr.shape[:2]
    e=16
    samples=np.concatenate([rgb[:e,:e].reshape(-1,3),rgb[:e,w-e:].reshape(-1,3),rgb[h-e:,:e].reshape(-1,3),rgb[h-e:,w-e:].reshape(-1,3)])
    bg=np.median(samples,axis=0)
    dist=np.sqrt(((rgb-bg)**2).sum(axis=2))
    mask=dist<34
    bgmask=np.zeros((h,w), dtype=bool); q=deque()
    for x in range(w):
        if mask[0,x]: q.append((0,x))
        if mask[h-1,x]: q.append((h-1,x))
    for y in range(h):
        if mask[y,0]: q.append((y,0))
        if mask[y,w-1]: q.append((y,w-1))
    while q:
        y,x=q.popleft()
        if bgmask[y,x] or not mask[y,x]: continue
        bgmask[y,x]=True
        if y>0: q.append((y-1,x))
        if y<h-1: q.append((y+1,x))
        if x>0: q.append((y,x-1))
        if x<w-1: q.append((y,x+1))
    # Eat AA fringe conservatively
    m=bgmask.copy(); m[:-1,:]|=bgmask[1:,:]; m[1:,:]|=bgmask[:-1,:]; m[:,:-1]|=bgmask[:,1:]; m[:,1:]|=bgmask[:,:-1]
    bgmask = m & (dist<58)
    arr[...,3]=np.where(bgmask,0,arr[...,3])
    return Image.fromarray(arr.astype(np.uint8),'RGBA')

def process(name):
    raw=Image.open(out/raw_files[name]).convert('RGBA')
    W,H=raw.size; cw,ch=W//cols,H//rows
    frames=[]
    for idx in range(8):
        cell=raw.crop(((idx%4)*cw,(idx//4)*ch,(idx%4+1)*cw,(idx//4+1)*ch))
        img=remove_gray_bg(cell)
        bbox=img.getbbox()
        if bbox:
            spr=img.crop(bbox)
            frames.append((idx,spr,bbox))
    print(name, len(frames), [(i,s.size,b) for i,s,b in frames])
    maxw=max(s.width for _,s,_ in frames); maxh=max(s.height for _,s,_ in frames)
    fw=max(512,maxw+100); fh=max(640,maxh+100)
    norm=[]; cdir=out/f'{name}_v1'; cdir.mkdir(exist_ok=True)
    for p in cdir.glob('*.png'): p.unlink()
    for i,s,b in frames:
        canvas=Image.new('RGBA',(fw,fh),(0,0,0,0))
        px=(fw-s.width)//2; py=fh-s.height-40
        canvas.alpha_composite(s,(px,py))
        norm.append(canvas); canvas.save(cdir/f'right_{i:02d}.png')
    left=[ImageOps.mirror(f) for f in norm]
    for i,f in enumerate(left): f.save(cdir/f'left_{i:02d}.png')
    sf=Image.new('RGBA',(fw*8,fh*2),(0,0,0,0))
    for i,f in enumerate(norm): sf.alpha_composite(f,(i*fw,0))
    for i,f in enumerate(left): sf.alpha_composite(f,(i*fw,fh))
    sf.save(out/f'{name}_right_left_spriteforge_v1.png')
    # contact
    check=Image.new('RGB',(fw*4,fh*2),(230,230,230)); d=ImageDraw.Draw(check)
    for yy in range(0,fh*2,32):
        for xx in range(0,fw*4,32):
            if (xx//32+yy//32)%2: d.rectangle((xx,yy,xx+31,yy+31),fill=(205,205,205))
    contact=check.convert('RGBA')
    for i,f in enumerate(norm): contact.alpha_composite(f,((i%4)*fw,(i//4)*fh))
    contact.convert('RGB').save(out/f'{name}_contact_v1.jpg', quality=92)
    all_frames[name]=(norm,left,fw,fh)

def panel_bg(w,h,label):
    im=Image.new('RGB',(w,h),(27,29,38)); d=ImageDraw.Draw(im)
    d.rectangle((0,int(h*.76),w,h),fill=(46,54,62))
    for x in range(-h,w,44): d.line((x,int(h*.76),x+int(h*.22),h),fill=(56,66,76),width=1)
    d.rounded_rectangle((12,12,min(w-12,18+len(label)*8+24),45), radius=8, fill=(10,12,18))
    d.text((24,21),label,fill=(240,243,250))
    return im.convert('RGBA')

for c in chars: process(c)
# Combined preview grid, 5 panels.
canvasW,canvasH=1280,720; panelW,panelH=426,360
positions=[(0,0),(426,0),(852,0),(0,360),(426,360)]
grid_dir=out/'octodex_more_preview_frames_v1'; grid_dir.mkdir(exist_ok=True)
for p in grid_dir.glob('*.png'): p.unlink()
for n in range(72):
    base=Image.new('RGB',(canvasW,canvasH),(18,20,28)).convert('RGBA')
    for idx,name in enumerate(chars):
        x0,y0=positions[idx]
        panel=panel_bg(panelW,panelH,labels[name])
        norm,left,fw,fh=all_frames[name]
        if name=='mona_classic_laptop':
            # Stay planted, loop the 8-frame bracing/laptop-aim action. No movement/projectiles.
            f=norm[n%8]
            x=(panelW-110)//2
            scale=min(.43,230/f.height)
        else:
            if n<36:
                f=norm[n%8]; x=35+int(n*(panelW-140)/35)
            else:
                f=left[n%8]; x=panelW-105-int((n-36)*(panelW-140)/35)
            scale=min(.36,205/f.height)
        spr=f.copy().resize((int(f.width*scale),int(f.height*scale)), Image.Resampling.LANCZOS)
        if name=='mona_classic_laptop': x=(panelW-spr.width)//2 + 20
        y=int(panelH*.79)-spr.height
        panel.alpha_composite(spr,(x,y))
        base.alpha_composite(panel,(x0,y0))
    base.convert('RGB').save(grid_dir/f'{n:04d}.png')
subprocess.run(['ffmpeg','-y','-framerate','12','-i',str(grid_dir/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'octodex_more_mona_laptop_preview_v1.mp4')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
# contacts montage
contact_all=Image.new('RGB',(512*5,680),(20,20,25)); d=ImageDraw.Draw(contact_all)
for i,name in enumerate(chars):
    im=Image.open(out/f'{name}_contact_v1.jpg').resize((512,640), Image.Resampling.LANCZOS).convert('RGB')
    contact_all.paste(im,(i*512,40)); d.text((i*512+16,14),labels[name],fill=(255,255,255))
contact_all.save(out/'octodex_more_contacts_v1.jpg', quality=90)
