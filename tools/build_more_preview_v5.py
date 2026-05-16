from PIL import Image, ImageOps, ImageDraw
from pathlib import Path
import subprocess
root=Path('/Users/jesusrubio/.openclaw/workspace/projects/octodex-sprites')
out=root/'out'
chars=['codercat','pythocat','octobiwan','labtocat','mona_classic_laptop']
labels={'codercat':'Codercat','pythocat':'Pythocat','octobiwan':'Octobiwan','labtocat':'Labtocat','mona_classic_laptop':'Mona classic: laptop clean'}

def clean_mona_laptop(img, phase=0):
    # Remove the previous fake arm/aim lines by painting a clean laptop-only silhouette over the prop area.
    im=img.copy()
    d=ImageDraw.Draw(im)
    dx=[0,1,2,1,0,-1,0,1][phase%8]
    dy=[0,-1,0,1,0,1,0,-1][phase%8]
    outline=(7,9,13,255)
    metal=(58,68,80,255)
    metal2=(86,98,112,255)
    screen=(20,32,38,255)
    # Tuned to the normalized Mona frames. No arms/laser/code lines, just a laptop.
    # Screen
    screen_poly=[(382+dx,292+dy),(510+dx,306+dy),(492+dx,364+dy),(370+dx,350+dy)]
    inner=[(397+dx,308+dy),(490+dx,318+dy),(480+dx,348+dy),(390+dx,338+dy)]
    # Keyboard/base
    base_poly=[(366+dx,366+dy),(500+dx,360+dy),(526+dx,389+dy),(388+dx,402+dy)]
    d.polygon(screen_poly, fill=metal, outline=outline)
    d.polygon(inner, fill=screen)
    d.polygon(base_poly, fill=metal2, outline=outline)
    # Tiny keyboard hints only on the laptop base, not external lines/effects.
    key=(35,40,46,255)
    for i in range(5):
        x=393+dx+i*18
        d.line((x,382+dy,x+10,381+dy), fill=key, width=2)
    return im

def load_frames(name):
    base=out/f'{name}_v1'
    rights=[]
    for i,p in enumerate(sorted(base.glob('right_*.png'))):
        im=Image.open(p).convert('RGBA')
        if name=='mona_classic_laptop':
            im=clean_mona_laptop(im,i)
        rights.append(im)
    return rights,[ImageOps.mirror(f) for f in rights]
all_frames={c:load_frames(c) for c in chars}
# Save clean Mona spriteforge sheet
mona_right,mona_left=all_frames['mona_classic_laptop']
fw,fh=mona_right[0].size
sheet=Image.new('RGBA',(fw*8,fh*2),(0,0,0,0))
for i,f in enumerate(mona_right): sheet.alpha_composite(f,(i*fw,0))
for i,f in enumerate(mona_left): sheet.alpha_composite(f,(i*fw,fh))
sheet.save(out/'mona_classic_laptop_clean_right_left_spriteforge_v5.png')
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
contact_all.save(out/'octodex_more_contacts_v5.jpg',quality=90)

def panel_bg(w,h,label):
    im=Image.new('RGB',(w,h),(27,29,38)); d=ImageDraw.Draw(im)
    d.rectangle((0,int(h*.76),w,h),fill=(46,54,62))
    for x in range(-h,w,44): d.line((x,int(h*.76),x+int(h*.22),h),fill=(56,66,76),width=1)
    d.rounded_rectangle((12,12,min(w-12,18+len(label)*8+24),45), radius=8, fill=(10,12,18))
    d.text((24,21),label,fill=(240,243,250))
    return im.convert('RGBA')
canvasW,canvasH=1280,720; panelW,panelH=426,360
positions=[(0,0),(426,0),(852,0),(0,360),(426,360)]
grid_dir=out/'octodex_more_preview_frames_v5'; grid_dir.mkdir(exist_ok=True)
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
subprocess.run(['ffmpeg','-y','-framerate','12','-i',str(grid_dir/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'octodex_more_mona_laptop_preview_v5_clean.mp4')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
