from PIL import Image, ImageOps, ImageDraw
from pathlib import Path
import numpy as np, subprocess
root=Path('/Users/jesusrubio/.openclaw/workspace/projects/octodex-sprites')
out=root/'out'
chars=['robotocat','dinotocat','securitocat','octoliberty','jetpacktocat']
cols,rows=4,2
all_frames={}
meta={}

def clean_cell(cell):
    cell=cell.convert('RGBA')
    arr=np.array(cell)
    rgb=arr[...,:3].astype(np.int16)
    h,w=arr.shape[:2]
    # Background color from corners/edges. Use median to tolerate slight variation.
    samples=[]
    edge=16
    samples.append(rgb[:edge,:edge].reshape(-1,3))
    samples.append(rgb[:edge,w-edge:].reshape(-1,3))
    samples.append(rgb[h-edge:,:edge].reshape(-1,3))
    samples.append(rgb[h-edge:,w-edge:].reshape(-1,3))
    bg=np.median(np.concatenate(samples), axis=0)
    dist=np.sqrt(((rgb-bg)**2).sum(axis=2))
    # Remove flat gray background + soft edges; keep actual gray bodies by only removing large bg-like regions.
    mask=dist < 34
    # Flood fill from image border through mask, so gray robot interiors are preserved if enclosed.
    from collections import deque
    bgmask=np.zeros((h,w), dtype=bool)
    q=deque()
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
    # Slightly expand to eat anti-aliased border only.
    for _ in range(1):
        m=bgmask.copy()
        m[:-1,:] |= bgmask[1:,:]
        m[1:,:] |= bgmask[:-1,:]
        m[:,:-1] |= bgmask[:,1:]
        m[:,1:] |= bgmask[:,:-1]
        bgmask = m & (dist < 55)
    arr[...,3]=np.where(bgmask,0,arr[...,3])
    return Image.fromarray(arr.astype(np.uint8),'RGBA')

def process(name):
    raw=Image.open(out/f'{name}_walk_raw_v2.png').convert('RGBA')
    W,H=raw.size; cw,ch=W//cols,H//rows
    frames=[]
    for idx in range(cols*rows):
        cell=raw.crop(((idx%cols)*cw,(idx//cols)*ch,(idx%cols+1)*cw,(idx//cols+1)*ch))
        img=clean_cell(cell)
        bbox=img.getbbox()
        if bbox:
            sprite=img.crop(bbox)
            frames.append((idx,sprite,bbox))
    print(name, 'frames', len(frames), 'bboxes', [(i,s.size,b) for i,s,b in frames])
    maxw=max(s.width for _,s,_ in frames); maxh=max(s.height for _,s,_ in frames)
    fw=max(512, maxw+90); fh=max(640, maxh+90)
    norm=[]; char_dir=out/f'{name}_v2'; char_dir.mkdir(exist_ok=True)
    for p in char_dir.glob('*.png'): p.unlink()
    for i,s,b in frames:
        canvas=Image.new('RGBA',(fw,fh),(0,0,0,0))
        px=(fw-s.width)//2; py=fh-s.height-38
        canvas.alpha_composite(s,(px,py))
        norm.append(canvas); canvas.save(char_dir/f'right_{i:02d}.png')
    left=[ImageOps.mirror(f) for f in norm]
    for i,f in enumerate(left): f.save(char_dir/f'left_{i:02d}.png')
    # Spriteforge-compatible sheet: row0 right, row1 left, 8 columns
    sf=Image.new('RGBA',(fw*8,fh*2),(0,0,0,0))
    for i,f in enumerate(norm): sf.alpha_composite(f,(i*fw,0))
    for i,f in enumerate(left): sf.alpha_composite(f,(i*fw,fh))
    sf.save(out/f'{name}_walk_right_left_spriteforge_v2.png')
    # Contact sheet right 4x2 over checker.
    check=Image.new('RGB',(fw*4,fh*2),(230,230,230)); d=ImageDraw.Draw(check)
    for yy in range(0,fh*2,32):
      for xx in range(0,fw*4,32):
        if (xx//32+yy//32)%2: d.rectangle((xx,yy,xx+31,yy+31),fill=(205,205,205))
    contact=check.convert('RGBA')
    for i,f in enumerate(norm): contact.alpha_composite(f,((i%4)*fw,(i//4)*fh))
    contact.convert('RGB').save(out/f'{name}_contact_v2.jpg', quality=92)
    all_frames[name]=(norm,left); meta[name]=(fw,fh)

def panel_bg(w,h,label):
    im=Image.new('RGB',(w,h),(31,33,42)); d=ImageDraw.Draw(im)
    d.rectangle((0,int(h*.76),w,h), fill=(47,55,63))
    for x in range(-h,w,44): d.line((x,int(h*.76),x+int(h*.22),h), fill=(57,67,76), width=1)
    d.rounded_rectangle((16,14,16+len(label)*9+20,45), radius=8, fill=(12,14,20))
    d.text((26,22), label, fill=(235,238,245))
    return im.convert('RGBA')

for c in chars: process(c)
print('meta', meta)
# individual previews and grid
for name in chars:
    norm,left=all_frames[name]
    pdir=out/f'{name}_preview_frames_v2'; pdir.mkdir(exist_ok=True)
    for p in pdir.glob('*.png'): p.unlink()
    W,H=960,540
    seq=[]
    for t in range(32): seq.append((norm[t%8],80+int(t*(W-240)/31)))
    for t in range(32): seq.append((left[t%8],W-160-int(t*(W-240)/31)))
    for n,(f,x) in enumerate(seq):
        canvas=panel_bg(W,H,name)
        spr=f.copy(); scale=min(.62, 300/spr.height)
        spr=spr.resize((int(spr.width*scale),int(spr.height*scale)), Image.Resampling.LANCZOS)
        y=int(H*.77)-spr.height
        canvas.alpha_composite(spr,(x,y))
        canvas.convert('RGB').save(pdir/f'{n:04d}.png')
    subprocess.run(['ffmpeg','-y','-framerate','12','-i',str(pdir/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(out/f'{name}_walk_preview_v2.mp4')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
# combined grid
canvasW,canvasH=1280,720; panelW,panelH=426,360
positions=[(0,0),(426,0),(852,0),(0,360),(426,360)]
grid_dir=out/'five_preview_frames_v2'; grid_dir.mkdir(exist_ok=True)
for p in grid_dir.glob('*.png'): p.unlink()
for n in range(64):
    base=Image.new('RGB',(canvasW,canvasH),(18,20,28)).convert('RGBA')
    for idx,name in enumerate(chars):
        x0,y0=positions[idx]
        panel=panel_bg(panelW,panelH,name)
        norm,left=all_frames[name]
        if n<32: f=norm[n%8]; x=35+int(n*(panelW-140)/31)
        else: f=left[n%8]; x=panelW-105-int((n-32)*(panelW-140)/31)
        spr=f.copy(); scale=min(.36, 205/spr.height)
        spr=spr.resize((int(spr.width*scale),int(spr.height*scale)), Image.Resampling.LANCZOS)
        y=int(panelH*.79)-spr.height
        panel.alpha_composite(spr,(x,y)); base.alpha_composite(panel,(x0,y0))
    base.convert('RGB').save(grid_dir/f'{n:04d}.png')
subprocess.run(['ffmpeg','-y','-framerate','12','-i',str(grid_dir/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'octodex_5_walk_preview_grid_v2.mp4')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
# contacts montage
contact_all=Image.new('RGB',(512*5,680),(20,20,25)); d=ImageDraw.Draw(contact_all)
for i,name in enumerate(chars):
    im=Image.open(out/f'{name}_contact_v2.jpg').resize((512,640), Image.Resampling.LANCZOS).convert('RGB')
    contact_all.paste(im,(i*512,40)); d.text((i*512+16,14), name, fill=(255,255,255))
contact_all.save(out/'octodex_5_contacts_v2.jpg', quality=90)
