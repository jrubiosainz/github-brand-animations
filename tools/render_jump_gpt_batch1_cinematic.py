#!/usr/bin/env python3
from pathlib import Path
import math, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets/spritesheets'
VIDEOS=ROOT/'previews/videos/jump-batches'; CONTACTS=ROOT/'previews/contact-sheets/jump-batches'; FRAMES=ROOT/'previews/frames/jump-batches/batch1_gpt_v5_cinematic'
for p in (VIDEOS,CONTACTS,FRAMES): p.mkdir(parents=True,exist_ok=True)
CHARS=[('mona','Mona'),('robotocat','Robotocat'),('dinotocat','Dinotocat'),('securitocat','Securitocat'),('octoliberty','OctoLiberty'),('jetpacktocat','Jetpacktocat'),('codercat','Codercat'),('pythocat','Pythocat')]

def font(size=24,bold=False):
    for p in ['/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf','/System/Library/Fonts/Supplemental/Helvetica.ttf','/System/Library/Fonts/SFNS.ttf']:
        try: return ImageFont.truetype(p,size)
        except Exception: pass
    return ImageFont.load_default()
FONT=font(26,True); SMALL=font(17,False)

def load(name):
    sheet=Image.open(ROOT/'assets'/'characters'/name/'jump'/f'{name}_jump_right_left_gpt_v3.png').convert('RGBA')
    fw,fh=sheet.width//8,sheet.height//2
    frames=[]
    for i in range(8):
        f=sheet.crop((i*fw,0,(i+1)*fw,fh))
        bbox=f.getbbox()
        if bbox: f=f.crop(bbox)
        frames.append(f)
    return frames
frames={n:load(n) for n,_ in CHARS}

def panel_bg(w,h,label,accent,n):
    im=Image.new('RGB',(w,h),(15,19,29)).convert('RGBA'); d=ImageDraw.Draw(im,'RGBA')
    for gy in range(12,h,34):
        for gx in range(10,w,34):
            if ((gx//34+gy//34+n//5)%8)==0: d.rounded_rectangle((gx,gy,gx+15,gy+15),radius=4,fill=accent+(38,))
    ground=int(h*.82); d.rectangle((0,ground,w,h),fill=(38,47,58,255))
    for x in range(-h,w,44): d.line((x,ground,x+int(h*.22),h),fill=(55,67,80,150),width=1)
    d.rounded_rectangle((16,14,min(w-16,36+len(label)*12),50),radius=10,fill=(5,9,18,220),outline=accent+(165,),width=1)
    d.text((28,22),label,font=SMALL,fill=(242,246,252))
    return im,ground

def pose_at(n):
    # 48-frame loop at 12fps: anticipation(8), launch(4), ballistic air(24), landing(7), recovery(5)
    k=n%48
    if k<8: return 0,0,1.12,.86,True       # crouch anticipation
    if k<12: return 1,-35,.92,1.12,False   # launch stretch
    if k<36:
        t=(k-12)/24
        y=-220*math.sin(math.pi*t)
        if t<.28: pose=2
        elif t<.56: pose=3
        elif t<.80: pose=4
        else: pose=5
        # slight ease: stronger hang at apex
        return pose,y,1.0,1.0,False
    if k<43: return 6,10,1.16,.82,True     # impact squash + dust
    return 7,0,1.0,1.0,False

def dust(panel,cx,ground,amount=1.0):
    d=ImageDraw.Draw(panel,'RGBA')
    for i in range(5):
        r=int((8+i*3)*amount); x=cx+(i-2)*18; y=ground+4+i%2*3
        d.ellipse((x-r,y-r//2,x+r,y+r//2),fill=(210,210,210,int(55*amount)))

W,H=1920,1080; panelW,panelH=W//4,H//2
positions=[(i*panelW,j*panelH) for j in range(2) for i in range(4)]
colors=[(88,166,255),(163,113,247),(63,185,80),(248,81,73),(210,168,255),(121,192,255),(255,171,112),(126,231,135)]
for p in FRAMES.glob('*.png'): p.unlink()
N=96
for n in range(N):
    canvas=Image.new('RGB',(W,H),(5,9,18)).convert('RGBA')
    for idx,(name,label) in enumerate(CHARS):
        x0,y0=positions[idx]; panel,ground=panel_bg(panelW,panelH,label,colors[idx],n)
        pose,yoff,sx,sy,impact=pose_at(n)
        f=frames[name][pose]
        scale=min(.49,285/f.height,325/f.width)
        spr=f.resize((max(1,int(f.width*scale*sx)),max(1,int(f.height*scale*sy))),Image.Resampling.LANCZOS)
        x=(panelW-spr.width)//2; y=int(ground-spr.height+yoff)
        # stronger squash/stretch is applied to the actual GPT jump pose; shadow follows the arc
        height_ratio=min(1,abs(yoff)/220)
        sh_w=int(spr.width*(.78-.42*height_ratio)); sh_h=max(6,int(20*(1-.55*height_ratio)))
        shadow=Image.new('RGBA',(max(1,sh_w),sh_h),(0,0,0,0)); sd=ImageDraw.Draw(shadow,'RGBA')
        sd.ellipse((0,0,sh_w-1,sh_h-1),fill=(0,0,0,int(118*(1-.50*height_ratio))))
        shadow=shadow.filter(ImageFilter.GaussianBlur(3))
        panel.alpha_composite(shadow,((panelW-shadow.width)//2,ground-shadow.height//2))
        if impact: dust(panel,panelW//2,ground,1.0 if (n%48)>=36 else .45)
        panel.alpha_composite(spr,(x,y))
        canvas.alpha_composite(panel,(x0,y0))
    canvas.convert('RGB').save(FRAMES/f'{n:04d}.png')
video=VIDEOS/'octodex_jump_batch1_gpt_v5_cinematic.mp4'
subprocess.run(['ffmpeg','-y','-framerate','12','-i',str(FRAMES/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
print('VIDEO',video)
