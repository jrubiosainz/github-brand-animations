from PIL import Image, ImageOps, ImageDraw, ImageFont
from pathlib import Path
import numpy as np, subprocess, os, math
root=Path('/Users/jesusrubio/.openclaw/workspace/projects/octodex-sprites')
out=root/'out'
chars=['robotocat','dinotocat','securitocat','octoliberty','jetpacktocat']
cols,rows=4,2
all_frames={}
meta={}

def clean_frames(name):
    raw=Image.open(out/f'{name}_walk_raw.png').convert('RGBA')
    W,H=raw.size; cw,ch=W//cols,H//rows
    frames=[]
    for idx in range(cols*rows):
        cell=raw.crop(((idx%cols)*cw,(idx//cols)*ch,(idx%cols+1)*cw,(idx//cols//cols+1)*ch if False else (idx//cols+1)*ch)).convert('RGBA')
        arr=np.array(cell)
        r,g,b,a=arr[...,0],arr[...,1],arr[...,2],arr[...,3]
        # Green key, intentionally conservative to keep costumes if green-ish.
        mask=(g>150) & (r<115) & (b<115) & (g>r+45) & (g>b+45)
        arr[...,3]=np.where(mask,0,a)
        # Despill near edges
        semi=(arr[...,3]>0) & (g>120) & (g>r+22) & (g>b+22)
        arr[...,1]=np.where(semi, np.minimum(arr[...,1], np.maximum(arr[...,0], arr[...,2])+18), arr[...,1])
        img=Image.fromarray(arr,'RGBA')
        bbox=img.getbbox()
        if bbox:
            sprite=img.crop(bbox)
            frames.append((idx,sprite,bbox))
    if len(frames) != 8:
        print('WARN frames', name, len(frames))
    maxw=max(s.width for _,s,_ in frames); maxh=max(s.height for _,s,_ in frames)
    fw=max(512, maxw+90); fh=max(640, maxh+90)
    norm=[]
    char_dir=out/name; char_dir.mkdir(exist_ok=True)
    for p in char_dir.glob('*.png'): p.unlink()
    for i,s,b in frames:
        canvas=Image.new('RGBA',(fw,fh),(0,0,0,0))
        px=(fw-s.width)//2
        py=fh-s.height-38
        canvas.alpha_composite(s,(px,py))
        norm.append(canvas)
        canvas.save(char_dir/f'right_{i:02d}.png')
    left=[ImageOps.mirror(f) for f in norm]
    for i,f in enumerate(left): f.save(char_dir/f'left_{i:02d}.png')
    # sheets
    for sheet_name, frs in [(f'{name}_walk_right_clean.png', norm), (f'{name}_walk_left_clean.png', left)]:
        sheet=Image.new('RGBA',(fw*4,fh*2),(0,0,0,0))
        for i,f in enumerate(frs): sheet.alpha_composite(f,((i%4)*fw,(i//4)*fh))
        sheet.save(out/sheet_name)
    sf=Image.new('RGBA',(fw*8,fh*2),(0,0,0,0))
    for i,f in enumerate(norm): sf.alpha_composite(f,(i*fw,0))
    for i,f in enumerate(left): sf.alpha_composite(f,(i*fw,fh))
    sf.save(out/f'{name}_walk_right_left_spriteforge.png')
    # contact sheet
    check=Image.new('RGB',(fw*4,fh*2),(230,230,230)); d=ImageDraw.Draw(check)
    for yy in range(0,fh*2,32):
        for xx in range(0,fw*4,32):
            if (xx//32+yy//32)%2: d.rectangle((xx,yy,xx+31,yy+31),fill=(205,205,205))
    contact=check.convert('RGBA')
    for i,f in enumerate(norm): contact.alpha_composite(f,((i%4)*fw,(i//4)*fh))
    contact.convert('RGB').save(out/f'{name}_contact.jpg', quality=92)
    meta[name]=(fw,fh)
    all_frames[name]=(norm,left)

for c in chars: clean_frames(c)
print('meta', meta)

# Individual previews.
def panel_bg(w,h,label=None):
    im=Image.new('RGB',(w,h),(31,33,42)); d=ImageDraw.Draw(im)
    d.rectangle((0,int(h*.76),w,h), fill=(47,55,63))
    for x in range(-h,w,44): d.line((x,int(h*.76),x+int(h*.22),h), fill=(57,67,76), width=1)
    if label:
        d.rounded_rectangle((16,14,16+len(label)*9+20,45), radius=8, fill=(12,14,20))
        d.text((26,22), label, fill=(235,238,245))
    return im.convert('RGBA')

for name in chars:
    norm,left=all_frames[name]
    pdir=out/f'{name}_preview_frames'; pdir.mkdir(exist_ok=True)
    for p in pdir.glob('*.png'): p.unlink()
    W,H=960,540
    seq=[]
    for t in range(32): seq.append((norm[t%8], 80+int(t*(W-240)/31)))
    for t in range(32): seq.append((left[t%8], W-160-int(t*(W-240)/31)))
    for n,(f,x) in enumerate(seq):
        canvas=panel_bg(W,H,name)
        spr=f.copy()
        scale=min(.62, 300/spr.height)
        spr=spr.resize((int(spr.width*scale),int(spr.height*scale)), Image.Resampling.LANCZOS)
        y=int(H*.77)-spr.height
        canvas.alpha_composite(spr,(x,y))
        canvas.convert('RGB').save(pdir/f'{n:04d}.png')
    subprocess.run(['ffmpeg','-y','-framerate','12','-i',str(pdir/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(out/f'{name}_walk_preview.mp4')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

# Combined reel: 5 panels in one 1280x720 video.
grid_dir=out/'five_preview_frames'; grid_dir.mkdir(exist_ok=True)
for p in grid_dir.glob('*.png'): p.unlink()
canvasW,canvasH=1280,720
panelW,panelH=426,360
positions=[(0,0),(426,0),(852,0),(0,360),(426,360)]
for n in range(64):
    base=Image.new('RGB',(canvasW,canvasH),(18,20,28)).convert('RGBA')
    for idx,name in enumerate(chars):
        x0,y0=positions[idx]
        panel=panel_bg(panelW,panelH,name)
        norm,left=all_frames[name]
        if n<32:
            f=norm[n%8]; x=35+int(n*(panelW-140)/31)
        else:
            f=left[n%8]; x=panelW-105-int((n-32)*(panelW-140)/31)
        spr=f.copy(); scale=min(.36, 205/spr.height)
        spr=spr.resize((int(spr.width*scale),int(spr.height*scale)), Image.Resampling.LANCZOS)
        y=int(panelH*.79)-spr.height
        panel.alpha_composite(spr,(x,y))
        base.alpha_composite(panel,(x0,y0))
    base.convert('RGB').save(grid_dir/f'{n:04d}.png')
subprocess.run(['ffmpeg','-y','-framerate','12','-i',str(grid_dir/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'octodex_5_walk_preview_grid.mp4')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
# montage contact for visual check
contacts=[]
for name in chars:
    im=Image.open(out/f'{name}_contact.jpg').resize((512,640), Image.Resampling.LANCZOS).convert('RGB')
    contacts.append((name, im))
contact_all=Image.new('RGB',(512*5,680),(20,20,25)); d=ImageDraw.Draw(contact_all)
for i,(name,im) in enumerate(contacts):
    contact_all.paste(im,(i*512,40)); d.text((i*512+16,14), name, fill=(255,255,255))
contact_all.save(out/'octodex_5_contacts.jpg', quality=90)
