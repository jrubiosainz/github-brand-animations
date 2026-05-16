from PIL import Image, ImageOps, ImageDraw
from pathlib import Path
import numpy as np, os, subprocess, math
root=Path('/Users/jesusrubio/.openclaw/workspace/projects/octodex-sprites')
out=root/'out'
out.mkdir(exist_ok=True)
raw=Image.open(out/'mona_walk_raw.png').convert('RGBA')
W,H=raw.size
cols,rows=4,2
cw,ch=W//cols,H//rows
frames=[]
# Chroma key green background; preserve black outline by requiring high green dominance.
for idx in range(cols*rows):
    x=(idx%cols)*cw; y=(idx//cols)*ch
    cell=raw.crop((x,y,x+cw,y+ch)).convert('RGBA')
    arr=np.array(cell)
    r,g,b,a=arr[...,0],arr[...,1],arr[...,2],arr[...,3]
    # solid/edge chroma: green high and significantly dominant
    mask=(g>145) & (g>r*1.18) & (g>b*1.18)
    arr[...,3]=np.where(mask,0,a)
    # despill pixels close to green edge but not transparent
    semi=(arr[...,3]>0) & (g>r*1.05) & (g>b*1.05) & (g>110)
    arr[...,1]=np.where(semi, np.minimum(arr[...,1], np.maximum(arr[...,0], arr[...,2])+20), arr[...,1])
    img=Image.fromarray(arr,'RGBA')
    bbox=img.getbbox()
    if not bbox:
        continue
    sprite=img.crop(bbox)
    frames.append((idx,sprite,bbox))
print('frames', len(frames), 'cell', cw,ch)
print('bboxes', [(i,s.size,b) for i,s,b in frames])
# Normalize canvas. Use max sprite size, padded, bottom-center anchored.
maxw=max(s.width for _,s,_ in frames); maxh=max(s.height for _,s,_ in frames)
fw=max(512, maxw+80); fh=max(512, maxh+80)
# keep manageable and square-ish for video
norm=[]
for i,s,b in frames:
    canvas=Image.new('RGBA',(fw,fh),(0,0,0,0))
    px=(fw-s.width)//2
    py=fh-s.height-34
    canvas.alpha_composite(s,(px,py))
    norm.append(canvas)
    canvas.save(out/f'frame_right_{i:02d}.png')
# left mirrored
left=[ImageOps.mirror(f) for f in norm]
for i,f in enumerate(left): f.save(out/f'frame_left_{i:02d}.png')
# sheets: right 4x2 and left 4x2
for name, frs in [('mona_walk_right_clean.png', norm), ('mona_walk_left_clean.png', left)]:
    sheet=Image.new('RGBA',(fw*4,fh*2),(0,0,0,0))
    for i,f in enumerate(frs): sheet.alpha_composite(f,((i%4)*fw,(i//4)*fh))
    sheet.save(out/name)
# combined horizontal rows for spriteforge-ish import
combined=Image.new('RGBA',(fw*8,fh*2),(0,0,0,0))
for i,f in enumerate(norm): combined.alpha_composite(f,(i*fw,0))
for i,f in enumerate(left): combined.alpha_composite(f,(i*fw,fh))
combined.save(out/'mona_walk_right_left_spriteforge.png')
# Make preview frames over a simple background, moving right then left.
preview_dir=out/'preview_frames'
preview_dir.mkdir(exist_ok=True)
for p in preview_dir.glob('*.png'): p.unlink()
bgW,bgH=960,540
def bg():
    im=Image.new('RGB',(bgW,bgH),(34,34,42))
    d=ImageDraw.Draw(im)
    # ground
    d.rectangle((0,405,bgW,bgH), fill=(48,56,64))
    for x in range(0,bgW,48): d.line((x,405,x+24,540), fill=(56,66,75), width=1)
    return im.convert('RGBA')
seq=[]
# 32 frames right, 32 left (4 loops each direction)
for t in range(32):
    f=norm[t%len(norm)]
    x=80 + int(t*(bgW-240)/31)
    seq.append(('r',f,x))
for t in range(32):
    f=left[t%len(left)]
    x=(bgW-160) - int(t*(bgW-240)/31)
    seq.append(('l',f,x))
for n,(_,f,x) in enumerate(seq):
    canvas=bg()
    # scale down for video if large
    spr=f.copy()
    scale=0.62
    spr=spr.resize((int(spr.width*scale),int(spr.height*scale)), Image.Resampling.LANCZOS)
    y=415-spr.height
    canvas.alpha_composite(spr,(x,y))
    canvas.convert('RGB').save(preview_dir/f'{n:04d}.png')
# contact sheet thumbnail over checker bg for inspection
check=Image.new('RGB',(fw*4,fh*2),(230,230,230))
d=ImageDraw.Draw(check)
for yy in range(0,fh*2,32):
  for xx in range(0,fw*4,32):
    if (xx//32+yy//32)%2: d.rectangle((xx,yy,xx+31,yy+31),fill=(205,205,205))
contact=check.convert('RGBA')
for i,f in enumerate(norm): contact.alpha_composite(f,((i%4)*fw,(i//4)*fh))
contact.convert('RGB').save(out/'mona_walk_right_contact.jpg', quality=92)
print('frame_size', fw,fh)
