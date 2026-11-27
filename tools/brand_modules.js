
/* =========== Brand modules: combo toys, task city, postcard, puzzle, family board =========== */
const BG=window.BRAND_GAME||{};

/* --- Combo: every dish gives a tree toy, toys combine into offers, 2 same = 1 any --- */
function mountCombo(root){
  const C=BG.combo,inv={};C.items.forEach(it=>inv[it.k]=0);
  root.innerHTML=`<div class="stage-c" style="padding-top:16px"><div class="cb-inv" id="cb-inv"></div></div>
    <div class="cb-buy" id="cb-buy">${C.items.map(it=>`<button class="btn alt" type="button" data-k="${it.k}">${it.src}</button>`).join('')}</div>
    <div class="block"><h3>Комбинации</h3><div class="cb-list" id="cb-list"></div></div>
    <div class="cb-swap"><b>Обмен:</b> 2 одинаковые игрушки на 1 недостающую
      <div class="row"><select id="cb-from" aria-label="Отдать две"></select><span>→</span><select id="cb-to" aria-label="Получить одну"></select><button class="btn alt" type="button" id="cb-sw">Обменять</button></div></div>`;
  const st=status();root.append(st,playerLine());
  const by=k=>C.items.find(i=>i.k===k);
  function draw(){
    $('cb-inv').innerHTML=C.items.map(it=>`<div class="cb-toy ${inv[it.k]?'on':''}"><span>${it.e}</span><b>${it.n}</b><small>× ${inv[it.k]}</small></div>`).join('');
    $('cb-list').innerHTML=C.combos.map((c,i)=>{const ok=Object.entries(c.need).every(([k,n])=>inv[k]>=n);
      return `<div class="cb-row ${ok?'ok':''}"><span>${Object.entries(c.need).map(([k,n])=>by(k).e.repeat(n)).join(' + ')}</span><b>${c.prize}</b><button class="btn ${ok?'':'alt'}" type="button" data-c="${i}" ${ok?'':'disabled'}>Забрать</button></div>`;}).join('');
    $('cb-from').innerHTML=C.items.filter(it=>inv[it.k]>=2).map(it=>`<option value="${it.k}">${it.e} ${it.n} ×2</option>`).join('')||'<option value="">нет пар</option>';
    $('cb-to').innerHTML=C.items.map(it=>`<option value="${it.k}">${it.e} ${it.n}</option>`).join('');
  }
  $('cb-buy').onclick=e=>{const b=e.target.closest('button');if(!b)return;const k=b.dataset.k;inv[k]++;draw();st.className='status ok';st.textContent=`Код ${rcode()} принят! ${by(k).src} = ${by(k).e} ${by(k).n}.`;};
  $('cb-list').onclick=e=>{const b=e.target.closest('button[data-c]');if(!b||b.disabled)return;const c=C.combos[+b.dataset.c];
    Object.entries(c.need).forEach(([k,n])=>inv[k]-=n);draw();modal({em:'🎄',title:c.prize,text:'Покажите экран на кассе.',code:rcode('GIFT')});};
  $('cb-sw').onclick=()=>{const f=$('cb-from').value,t=$('cb-to').value;if(!f){st.className='status bad';st.textContent='Для обмена нужны две одинаковые игрушки.';return;}
    if(f===t){st.className='status bad';st.textContent='Выберите другую игрушку.';return;}inv[f]-=2;inv[t]++;draw();st.className='status ok';st.textContent=`Обмен: 2 × ${by(f).n} → ${by(t).e} ${by(t).n}.`;};
  draw();
}

/* --- Task city: each task done (code at the till) lights a house --- */
function mountCity(root){
  const T=BG.city;const done=new Set();
  root.innerHTML=`<div class="stage-c" style="padding-top:16px"><div class="stage-top"><span>Огни города: <b id="ct-n"></b></span><b id="ct-l"></b></div>
    <div class="ct-grid" id="ct-grid"></div></div><p class="mic-hint">Нажмите на дом: в игре задание засчитывается кодом с чека.</p>`;
  const st=status();root.append(st,playerLine());
  function draw(){$('ct-n').textContent=`${done.size} из ${T.length}`;$('ct-l').textContent=done.size>=T.length?'Город сияет!':`Осталось: ${T.length-done.size}`;
    $('ct-grid').innerHTML=T.map((t,i)=>`<button type="button" class="ct-house ${done.has(i)?'lit':''}" data-i="${i}"><span>${done.has(i)?'🏠':'🏚️'}</span><b>${t.e} ${t.t}</b>${done.has(i)?'<small>✓ выполнено</small>':''}</button>`).join('');}
  $('ct-grid').onclick=e=>{const b=e.target.closest('button');if(!b)return;const i=+b.dataset.i;if(done.has(i)){st.className='status';st.textContent='Это задание уже выполнено.';return;}
    done.add(i);draw();st.className='status ok';st.textContent=`Код ${rcode()} принят! Дом зажёг огни.`;
    if(T[i].bonus)setTimeout(()=>modal({em:T[i].e,title:T[i].bonus,text:'Бонус за задание.',code:rcode('CITY')}),300);
    if(done.size>=T.length)setTimeout(()=>modal({em:'🌟',title:'Город сияет!',text:BG.cityPrize,code:rcode('CITY')}),700);};
  draw();
}

/* --- Postcard: recipient, wish, optional photo, rendered on the phone --- */
function mountCard(root){
  const P=BG.card;let photo=null;
  root.innerHTML=`<div class="cd-form">
      <label>Кому<select id="cd-to">${P.to.map((t,i)=>`<option value="${i}">${t.n}</option>`).join('')}</select></label>
      <label>От кого<input type="text" id="cd-from" maxlength="24" placeholder="Ваше имя" style="text-transform:none;width:100%"></label>
      <label>Пожелание<textarea id="cd-wish" rows="3" maxlength="160"></textarea></label>
      ${P.photo?`<label class="btn alt cd-ph" for="cd-file">📷 ${P.photoLabel||'Добавить фото'}</label><input id="cd-file" type="file" accept="image/*" hidden>`:''}
      <div class="row">${P.themes.map((t,i)=>`<button type="button" class="cd-theme ${i?'':'on'}" data-t="${i}" style="background:linear-gradient(160deg,${t[0]},${t[1]})" aria-label="Оформление ${i+1}"></button>`).join('')}</div>
    </div>
    <div class="stage-c" style="padding:14px"><canvas id="cd-c" width="600" height="800" class="cd-canvas"></canvas></div>
    <div class="row"><a class="btn hot" id="cd-save" download="novogodnyaya-otkrytka.png">💾 Сохранить открытку</a>${P.game?`<a class="btn alt" href="#${P.game}">🎮 Мини-игра на открытке</a>`:''}</div>
    <p class="mic-hint">${P.photo?'Фото никуда не отправляется: открытка собирается прямо в телефоне.':'Открытка собирается прямо в телефоне.'}</p>`;
  let theme=0;const cv=$('cd-c'),x=cv.getContext('2d');
  const setWish=()=>{$('cd-wish').value=P.to[+$('cd-to').value].w;};setWish();
  function wrap(t,mx,y,maxW,lh){const words=t.split(' ');let line='';for(const w of words){const test=line?line+' '+w:w;if(x.measureText(test).width>maxW&&line){x.fillText(line,mx,y);line=w;y+=lh;}else line=test;}x.fillText(line,mx,y);return y;}
  function draw(){const[t0,t1]=P.themes[theme];const g=x.createLinearGradient(0,0,600,800);g.addColorStop(0,t0);g.addColorStop(1,t1);x.fillStyle=g;x.fillRect(0,0,600,800);
    x.fillStyle='rgba(255,255,255,.75)';for(let i=0;i<70;i++){x.beginPath();x.arc((i*137)%600,(i*89)%800,(i%3)+1.5,0,7);x.fill();}
    x.textAlign='center';x.fillStyle='#fff';x.font='800 30px '+getComputedStyle(document.body).fontFamily;x.fillText(P.brand,300,60);
    let y=120;
    if(photo){const s=300,r=photo.width/photo.height,sw=r>1?photo.height:photo.width,sx=(photo.width-sw)/2,sy=(photo.height-sw)/2;x.save();x.beginPath();x.arc(300,y+s/2,s/2,0,7);x.closePath();x.clip();x.drawImage(photo,sx,sy,sw,sw,150,y,s,s);x.restore();
      x.strokeStyle='#fff';x.lineWidth=8;x.beginPath();x.arc(300,y+s/2,s/2,0,7);x.stroke();y+=s+70;}
    else{x.font='130px serif';x.fillText(P.to[+$('cd-to').value].e,300,y+140);y+=210;}
    x.font='900 46px '+getComputedStyle(document.body).fontFamily;x.fillText('С Новым годом,',300,y);x.fillText(P.to[+$('cd-to').value].hi+'!',300,y+54);
    x.font='600 30px '+getComputedStyle(document.body).fontFamily;const ye=wrap($('cd-wish').value,300,y+110,520,38);
    const fr=$('cd-from').value.trim();if(fr){x.font='italic 600 26px '+getComputedStyle(document.body).fontFamily;x.fillText('С любовью, '+fr,300,Math.min(ye+56,760));}
    try{$('cd-save').href=cv.toDataURL('image/png');}catch(e){}}
  root.querySelector('.cd-form').addEventListener('input',e=>{if(e.target.id==='cd-to')setWish();draw();});
  root.querySelectorAll('.cd-theme').forEach(b=>b.onclick=()=>{theme=+b.dataset.t;root.querySelectorAll('.cd-theme').forEach(z=>z.classList.toggle('on',z===b));draw();});
  if(P.photo)$('cd-file').onchange=e=>{const f=e.target.files[0];if(!f)return;const img=new Image();img.onload=()=>{photo=img;draw();};img.src=URL.createObjectURL(f);};
  document.fonts&&document.fonts.ready.then(draw);draw();
}

/* --- Puzzle: every code opens one piece of a picture --- */
function mountPuzzle(root){
  const Z=BG.puzzle,N=9;let open=new Set();const used=new Set();
  root.innerHTML=`<div class="stage-c" style="padding-top:40px"><div class="stage-top"><span>Открыто: <b id="pz-n"></b></span><b id="pz-l"></b></div>
    <div class="pz" id="pz" style="background-image:url(${A+Z.img})">${Array.from({length:N},(_,i)=>`<i data-i="${i}"><span>${i+1}</span></i>`).join('')}</div></div>`;
  const st=status(),bar=scanBar((c,again)=>{if(again||used.has(c)){st.className='status bad';st.textContent=`Код ${c} уже использован.`;return;}
    if(open.size>=N){st.className='status';st.textContent='Пазл уже собран. Нажмите «Начать заново».';return;}
    used.add(c);const rest=[...Array(N).keys()].filter(i=>!open.has(i));open.add(rest[Math.floor(Math.random()*rest.length)]);draw();
    st.className='status ok';st.textContent=open.size>=N?Z.done:`Код ${c} принят! Открыт кусочек ${open.size} из ${N}.`;
    if(open.size>=N)setTimeout(()=>modal({em:'🧩',title:Z.done,text:Z.prize,code:rcode('PUZ')}),600);},'Сканировать код с покупки');
  const rs=document.createElement('button');rs.className='btn alt';rs.type='button';rs.textContent='Начать заново';rs.onclick=()=>{open=new Set();used.clear();draw();st.textContent='';};
  root.append(bar,st,playerLine(),rs);
  function draw(){$('pz-n').textContent=`${open.size} из ${N}`;$('pz-l').textContent=open.size>=N?'Собрано!':`Осталось: ${N-open.size}`;
    $('pz').querySelectorAll('i').forEach(t=>t.classList.toggle('open',open.has(+t.dataset.i)));}
  draw();
}

/* --- Family board game: one phone, the family takes turns --- */
function mountBoard(root){
  const B=BG.board,L=B.cells.length;const pl=[{e:'👧',p:0},{e:'👨',p:0}];let turn=0,busy=false;
  root.innerHTML=`<div class="stage-c" style="padding-top:16px"><div class="bd" id="bd"></div></div>
    <div class="row"><button class="btn hot" type="button" id="bd-roll">🎲 Бросить кубик</button><span class="mic-hint" id="bd-turn"></span></div>`;
  const st=status(),rs=document.createElement('button');rs.className='btn alt';rs.type='button';rs.textContent='Начать заново';
  rs.onclick=()=>{pl.forEach(p=>p.p=0);turn=0;draw();st.textContent='';};root.append(st,rs);
  function draw(){$('bd').innerHTML=B.cells.map((c,i)=>`<div class="bd-c ${i===L-1?'fin':''}"><small>${i+1}</small><span>${c.e}</span><b>${c.t}</b><em>${pl.filter(p=>p.p===i).map(p=>p.e).join('')}</em></div>`).join('');
    $('bd-turn').textContent=`Ходит ${pl[turn].e}`;}
  $('bd-roll').onclick=async()=>{if(busy)return;const P=pl[turn];if(P.p>=L-1)return;busy=true;const d=1+Math.floor(Math.random()*3);
    for(let s=0;s<d&&P.p<L-1;s++){P.p++;draw();await sleep(220);}
    const c=B.cells[P.p];st.className='status ok';st.textContent=`${P.e} выбросил ${d}: ${c.e} ${c.t}`;
    if(P.p>=L-1)setTimeout(()=>modal({em:'🏆',title:'Семья дошла до финиша!',text:B.prize,code:rcode('FAM')}),400);
    turn=(turn+1)%pl.length;draw();busy=false;};
  draw();
}
