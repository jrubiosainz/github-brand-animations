from PIL import Image, ImageOps, ImageDraw
from pathlib import Path
import subprocess
root=Path('/Users/jesusrubio/.openclaw/workspace/projects/octodex-sprites')
out=root/'out'
chars=['codercat','pythocat','octobiwan','labtocat','mona_classic_laptop']
labels={'codercat':'Codercat','pythocat':'Pythocat','octobiwan':'Octobiwan','labtocat':'Labtocat','mona_classic_laptop':'Mona classic: laptop aim'}

def enhance_mona(img, phase=0):
    # Manual pixel-art overlay to force-read as two-paw laptop aiming stance.
    im=img.copy()
    d=ImageDraw.Draw(im)
    # subtle bob/recoil
    dx=[0,2,4,2,0,-1,1,0][phase%8]
    dy=[0,-1,0,1,0,1,0,-1][phase%8]
    # Coordinates tuned for 578x640 normalized Mona frames.
    # Arms behind paws, clearly visible.
    dark=(22,24,30,255)
    outline=(6,8,12,255)
    paw=(225,228,222,255)
    paw_outline=(18,20,26,255)
    metal=(66,76,88,255)
    metal2=(96,112,130,255)
    screen=(18,38,42,255)
    green=(100,230,150,255)
    # two arms, extended forward
    d.line([(250,340+dy),(392+dx,320+dy)], fill=outline, width=22)
    d.line([(252,390+dy),(397+dx,372+dy)], fill=outline, width=22)
    d.line([(252,340+dy),(392+dx,320+dy)], fill=dark, width=14)
    d.line([(254,390+dy),(397+dx,372+dy)], fill=dark, width=14)
    # laptop screen/base, on top of arm ends
    screen_poly=[(388+dx,282+dy),(512+dx,303+dy),(494+dx,365+dy),(374+dx,344+dy)]
    base_poly=[(370+dx,367+dy),(500+dx,360+dy),(526+dx,388+dy),(390+dx,399+dy)]
    d.polygon(screen_poly, fill=metal, outline=outline)
    d.polygon([(402+dx,298+dy),(493+dx,313+dy),(482+dx,350+dy),(394+dx,337+dy)], fill=screen)
    # contained code pixels ON screen only
    for i in range(5):
        x=408+dx+i*15; y=312+dy+(i%2)*9
        d.line([(x,y),(x+8,y)], fill=green, width=2)
    d.polygon(base_poly, fill=metal2, outline=outline)
    # paws visible gripping both sides
    d.ellipse((372+dx,300+dy,412+dx,338+dy), fill=paw, outline=paw_outline, width=3)
    d.ellipse((394+dx,358+dy,438+dx,396+dy), fill=paw, outline=paw_outline, width=3)
    return im

def load_frames(name):
    base=out/f'{name}_v1'
    rights=[]
    for i,p in enumerate(sorted(base.glob('right_*.png'))):
        im=Image.open(p).convert('RGBA')
        if name=='mona_classic_laptop': im=enhance_mona(im,i)
        rights.append(im)
    lefts=[]
    for i,im in enumerate(rights):
        lefts.append(ImageOps.mirror(im))
    return rights,lefts
all_frames={c:load_frames(c) for c in chars}
# Save enhanced mona spriteforge sheet for later editing
mona_right,mona_left=all_frames['mona_classic_laptop']
fw,fh=mona_right[0].size
sheet=Image.new('RGBA',(fw*8,fh*2),(0,0,0,0))
for i,f in enumerate(mona_right): sheet.alpha_composite(f,(i*fw,0))
for i,f in enumerate(mona_left): sheet.alpha_composite(f,(i*fw,fh))
sheet.save(out/'mona_classic_laptop_right_left_spriteforge_v4.png')
# Contact montage with enhanced mona in its column
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
contact_all.save(out/'octodex_more_contacts_v4.jpg',quality=90)

def panel_bg(w,h,label):
    im=Image.new('RGB',(w,h),(27,29,38)); d=ImageDraw.Draw(im)
    d.rectangle((0,int(h*.76),w,h),fill=(46,54,62))
    for x in range(-h,w,44): d.line((x,int(h*.76),x+int(h*.22),h),fill=(56,66,76),width=1)
    d.rounded_rectangle((12,12,min(w-12,18+len(label)*8+24),45), radius=8, fill=(10,12,18))
    d.text((24,21),label,fill=(240,243,250))
    return im.convert('RGBA')
canvasW,canvasH=1280,720; panelW,panelH=426,360
positions=[(0,0),(426,0),(852,0),(0,360),(426,360)]
grid_dir=out/'octodex_more_preview_frames_v4'; grid_dir.mkdir(exist_ok=True)
for p in grid_dir.glob('*.png'): p.unlink()
for n in range(72):
    base=Image.new('RGB',(canvasW,canvasH),(18,20,28)).convert('RGBA')
    for idx,name in enumerate(chars):
        x0,y0=positions[idx]
        panel=panel_bg(panelW,panelH,labels[name])
        norm,left=all_frames[name]
        if name=='mona_classic_laptop':
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
subprocess.run(['ffmpeg','-y','-framerate','12','-i',str(grid_dir/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'octodex_more_mona_laptop_preview_v4.mp4')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
