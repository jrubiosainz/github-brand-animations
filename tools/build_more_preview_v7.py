from PIL import Image, ImageOps, ImageDraw
from pathlib import Path
import numpy as np, subprocess, math
from collections import deque
root=Path('/Users/jesusrubio/.openclaw/workspace/projects/octodex-sprites')
out=root/'out'
chars=['codercat','pythocat','octobiwan','labtocat','mona_classic_clean']
labels={'codercat':'Codercat','pythocat':'Pythocat','octobiwan':'Octobiwan','labtocat':'Labtocat','mona_classic_clean':'Mona clean laptop'}

def remove_gray_bg(img):
    img=img.convert('RGBA')
    arr=np.array(img)
    rgb=arr[...,:3].astype(np.int16); h,w=arr.shape[:2]
    e=max(12,min(h,w)//64)
    samples=np.concatenate([rgb[:e,:e].reshape(-1,3),rgb[:e,w-e:].reshape(-1,3),rgb[h-e:,:e].reshape(-1,3),rgb[h-e:,w-e:].reshape(-1,3)])
    bg=np.median(samples,axis=0)
    dist=np.sqrt(((rgb-bg)**2).sum(axis=2))
    mask=dist<36
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
    # soft fringe
    m=bgmask.copy(); m[:-1,:]|=bgmask[1:,:]; m[1:,:]|=bgmask[:-1,:]; m[:,:-1]|=bgmask[:,1:]; m[:,1:]|=bgmask[:,:-1]
    bgmask=m & (dist<62)
    arr[...,3]=np.where(bgmask,0,arr[...,3])
    return Image.fromarray(arr.astype(np.uint8),'RGBA')

def load_walk(name):
    base=out/f'{name}_v1'
    rights=[Image.open(p).convert('RGBA') for p in sorted(base.glob('right_*.png'))]
    return rights,[ImageOps.mirror(f) for f in rights]

def load_clean_mona():
    raw=Image.open(out/'mona_classic_clean_single_laptop_pose_v1.png').convert('RGBA')
    img=remove_gray_bg(raw)
    bbox=img.getbbox()
    sprite=img.crop(bbox)
    # Normalize to 578x640 canvas to match old panel feel, bottom anchored.
    fw,fh=578,640
    # generated single pose is high-res; scale to fit 500h
    scale=min(500/sprite.height, 500/sprite.width)
    sprite=sprite.resize((int(sprite.width*scale), int(sprite.height*scale)), Image.Resampling.LANCZOS)
    frames=[]
    for i in range(8):
        # deterministic tiny bracing animation: no facial changes, no new drawing.
        dy=[0,-2,-1,1,0,1,-1,0][i]
        dx=[0,1,2,1,0,-1,0,1][i]
        # scale/recoil very small
        s=1.0 + [0,.003,.005,.003,0,-.002,0,.002][i]
        spr=sprite.resize((int(sprite.width*s), int(sprite.height*s)), Image.Resampling.LANCZOS)
        canvas=Image.new('RGBA',(fw,fh),(0,0,0,0))
        px=(fw-spr.width)//2 + dx + 8
        py=fh-spr.height-34 + dy
        canvas.alpha_composite(spr,(px,py))
        frames.append(canvas)
    return frames,[ImageOps.mirror(f) for f in frames]

all_frames={
    'codercat': load_walk('codercat'),
    'pythocat': load_walk('pythocat'),
    'octobiwan': load_walk('octobiwan'),
    'labtocat': load_walk('labtocat'),
    'mona_classic_clean': load_clean_mona(),
}
# Save clean mona frames and spriteforge sheet
mona_dir=out/'mona_classic_clean_v7'; mona_dir.mkdir(exist_ok=True)
for p in mona_dir.glob('*.png'): p.unlink()
mr,ml=all_frames['mona_classic_clean']; fw,fh=mr[0].size
for i,f in enumerate(mr): f.save(mona_dir/f'right_{i:02d}.png')
for i,f in enumerate(ml): f.save(mona_dir/f'left_{i:02d}.png')
sheet=Image.new('RGBA',(fw*8,fh*2),(0,0,0,0))
for i,f in enumerate(mr): sheet.alpha_composite(f,(i*fw,0))
for i,f in enumerate(ml): sheet.alpha_composite(f,(i*fw,fh))
sheet.save(out/'mona_classic_clean_laptop_right_left_spriteforge_v7.png')
# Contact montage
contact_all=Image.new('RGB',(512*5,680),(20,20,25)); d=ImageDraw.Draw(contact_all)
for i,name in enumerate(chars):
    rights,_=all_frames[name]
    fw,fh=rights[0].size
    check=Image.new('RGB',(fw*4,fh*2),(230,230,230)); dc=ImageDraw.Draw(check)
    for yy in range(0,fh*2,32):
        for xx in range(0,fw*4,32):
            if (xx//32+yy//32)%2: dc.rectangle((xx,yy,xx+31,yy+31),fill=(205,205,205))
    contact=check.convert('RGBA')
    for j,f in enumerate(rights): contact.alpha_composite(f,((j%4)*fw,(j//4)*fh))
    im=contact.convert('RGB').resize((512,640),Image.Resampling.LANCZOS)
    contact_all.paste(im,(i*512,40)); d.text((i*512+16,14),labels[name],fill=(255,255,255))
contact_all.save(out/'octodex_more_contacts_v7_clean_mona.jpg',quality=90)

def panel_bg(w,h,label):
    im=Image.new('RGB',(w,h),(27,29,38)); d=ImageDraw.Draw(im)
    d.rectangle((0,int(h*.76),w,h),fill=(46,54,62))
    for x in range(-h,w,44): d.line((x,int(h*.76),x+int(h*.22),h),fill=(56,66,76),width=1)
    d.rounded_rectangle((12,12,min(w-12,18+len(label)*8+24),45), radius=8, fill=(10,12,18))
    d.text((24,21),label,fill=(240,243,250))
    return im.convert('RGBA')
canvasW,canvasH=1280,720; panelW,panelH=426,360
positions=[(0,0),(426,0),(852,0),(0,360),(426,360)]
grid_dir=out/'octodex_more_preview_frames_v7_clean_mona'; grid_dir.mkdir(exist_ok=True)
for p in grid_dir.glob('*.png'): p.unlink()
for n in range(72):
    base=Image.new('RGB',(canvasW,canvasH),(18,20,28)).convert('RGBA')
    for idx,name in enumerate(chars):
        x0,y0=positions[idx]
        panel=panel_bg(panelW,panelH,labels[name])
        norm,left=all_frames[name]
        if name=='mona_classic_clean':
            f=norm[n%8]
            scale=min(.46,235/f.height)
            spr=f.copy().resize((int(f.width*scale),int(f.height*scale)),Image.Resampling.LANCZOS)
            x=(panelW-spr.width)//2+12
        else:
            if n<36:
                f=norm[n%8]; x=35+int(n*(panelW-140)/35)
            else:
                f=left[n%8]; x=panelW-105-int((n-36)*(panelW-140)/35)
            scale=min(.36,205/f.height)
            spr=f.copy().resize((int(f.width*scale),int(f.height*scale)),Image.Resampling.LANCZOS)
        y=int(panelH*.79)-spr.height
        panel.alpha_composite(spr,(x,y))
        base.alpha_composite(panel,(x0,y0))
    base.convert('RGB').save(grid_dir/f'{n:04d}.png')
subprocess.run(['ffmpeg','-y','-framerate','12','-i',str(grid_dir/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'octodex_more_mona_laptop_preview_v7_clean_from_scratch.mp4')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
