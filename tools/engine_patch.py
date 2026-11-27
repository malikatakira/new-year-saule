"""Make demo games take brand colours and brand items (applied to a page in place)."""
import sys
p=sys.argv[1];s=open(p).read()
def rep(o,n):
    global s
    if n in s: return
    assert s.count(o)==1,(p,s.count(o),o[:60]); s=s.replace(o,n)
rep("canvas.game{width:100%;max-width:100%;border-radius:20px;background:linear-gradient(#1E6B3A,#154A2A);",
    "canvas.game{width:100%;max-width:100%;border-radius:20px;background:linear-gradient(var(--berry),var(--red-deep));")
rep("const TOYC=['#C8202A','#1E6B3A','#F2B33D','#7b5cff','#2a8fd6','#E2457A'];",
    "const TOYC=['#C8202A','#1E6B3A','#F2B33D','#7b5cff','#2a8fd6','#E2457A'];\nconst BRAND=window.BRAND_GAME||{};")
rep("""<circle r="11" fill="${c}"/><circle cx="-4" cy="-4" r="3.4" fill="#fff" opacity=".6"/></g></g>`;}""",
    """${BRAND.toys?`<circle r="12" fill="#fff" stroke="${c}" stroke-width="2.5"/><text y="5" text-anchor="middle" font-size="13">${BRAND.toys[i%BRAND.toys.length]}</text>`:`<circle r="11" fill="${c}"/><circle cx="-4" cy="-4" r="3.4" fill="#fff" opacity=".6"/>`}</g></g>`;}""")
rep("const g=x.createLinearGradient(0,0,r.width,r.height);g.addColorStop(0,'#C8202A');g.addColorStop(1,'#9E1A20');",
    "const cs=getComputedStyle(document.documentElement),g=x.createLinearGradient(0,0,r.width,r.height);g.addColorStop(0,cs.getPropertyValue('--berry').trim()||'#C8202A');g.addColorStop(1,cs.getPropertyValue('--red-deep').trim()||'#9E1A20');")
rep("if(img.complete)x.drawImage(img,G.px-38,280,76,76*img.naturalHeight/img.naturalWidth);",
    "if(BRAND.catcher){x.font='58px serif';x.fillText(BRAND.catcher,G.px,330);}else if(img.complete)x.drawImage(img,G.px-38,280,76,76*img.naturalHeight/img.naturalWidth);")
open(p,'w').write(s);print('patched',p)
