"""Build a branded New Year proposal page from shu-newyear/index.html.

Usage: python3 tools/make_brand_kp.py <brand>   (zenchenko | kulikov)
Writes <brand>/index.html and copies shared assets into <brand>/assets/.
"""
import json, shutil, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = (ROOT / 'shu-newyear' / 'index.html').read_text()

# ---------- battle (vote with purchases) module, shared ----------
BATTLE_JS = r"""
/* =========== Battle: every code is a vote =========== */
function mountBattle(root){
  const O=BATTLE_OPTS.map(o=>({...o}));let mine=null;
  root.innerHTML=`<div class="stage-c" style="padding-top:16px"><div class="bt-rows" id="bt-rows"></div><p class="mic-hint" style="text-align:center;margin-top:8px">${BATTLE_NOTE}</p></div>`;
  const pick=document.createElement('div');pick.className='bt-pick';pick.innerHTML=O.map((o,i)=>`<button class="btn alt" type="button" data-i="${i}">${o.e} ${o.n}</button>`).join('');
  const st=status();
  const bar=scanBar((c,again)=>{if(again){st.className='status bad';st.textContent=`Код ${c} уже использован.`;return;}
    if(mine===null){st.className='status';st.textContent='Сначала выберите, за кого играете.';return;}
    O[mine].v+=1+Math.floor(Math.random()*3);draw();st.className='status ok';st.textContent=`Код ${c} принят! +1 голос за «${O[mine].n}».`;},'Сканировать код и проголосовать');
  root.append(pick,bar,st,playerLine());
  pick.onclick=e=>{const b=e.target.closest('button');if(!b)return;mine=+b.dataset.i;pick.querySelectorAll('button').forEach((x,i)=>x.className='btn '+(i===mine?'':'alt'));st.className='status ok';st.textContent=`Вы играете за «${O[mine].n}». Каждый код с покупки добавляет голос.`;draw();};
  function draw(){const tot=O.reduce((a,o)=>a+o.v,0),max=Math.max(...O.map(o=>o.v));
    $('bt-rows').innerHTML=O.map((o,i)=>{const p=Math.round(o.v/tot*100);return `<div class="bt-row ${i===mine?'mine':''}"><span class="bt-e">${o.e}</span><div class="bt-b"><div class="bt-t"><b>${o.n}${o.v===max?' · лидер':''}</b><span>${p}%</span></div><div class="bt-bar"><i style="width:${p}%"></i></div></div></div>`;}).join('');}
  draw();
}
"""
BATTLE_CSS = """.kp-label{display:inline-block;font:700 12px var(--body);letter-spacing:.12em;text-transform:uppercase;padding:5px 12px;border-radius:99px;background:rgba(255,255,255,.16);color:#fff;margin-bottom:8px}
.bt-rows{display:flex;flex-direction:column;gap:10px;width:100%}
.bt-row{display:grid;grid-template-columns:44px 1fr;gap:10px;align-items:center;padding:6px;border-radius:14px}
.bt-row.mine{background:var(--soft)}
.bt-e{width:44px;height:44px;border-radius:50%;background:var(--card);border:2px solid var(--line);display:grid;place-items:center;font-size:24px}
.bt-b{min-width:0;display:flex;flex-direction:column;gap:4px}
.bt-t{display:flex;justify-content:space-between;gap:8px;font-size:14px}
.bt-bar{height:10px;border-radius:6px;background:rgba(0,0,0,.08);overflow:hidden}
.bt-bar i{display:block;height:100%;border-radius:6px;background:linear-gradient(90deg,var(--berry),var(--gold));transition:width .8s}
.bt-pick{display:flex;flex-wrap:wrap;gap:8px}
"""

def extra(title, html):
    return f"extra({json.dumps(title, ensure_ascii=False)},{json.dumps(html, ensure_ascii=False)})"

def games_js(games):
    out = []
    for g in games:
        ex = ','.join(extra(t, h) for t, h in g['extras'])
        pk = json.dumps(g['pk'], ensure_ascii=False)
        fields = {k: g[k] for k in ('id', 'em', 'title', 'short', 'from', 'term', 'lead', 'how')}
        f = json.dumps(fields, ensure_ascii=False)[:-1]
        out.append(f"{f},\"extras\":[{ex}],\"pk\":{pk}}}")
    return 'const GAMES=[\n ' + ',\n '.join(out) + '\n];\n\n'

def build(cfg):
    s = BASE
    def rep(o, n, count=1):
        nonlocal s
        assert s.count(o) == count, (s.count(o), o[:70])
        s = s.replace(o, n)
    # head
    i = s.index('<link rel="stylesheet" href="https://fonts.googleapis.com'); j = s.index('>', i) + 1
    s = s[:i] + f'<link rel="stylesheet" href="{cfg["fonts"]}">' + s[j:]
    rep('<title>Новогодние игры SHŪ</title>', f'<title>{cfg["name"]}: новогодние игры</title>')
    a = s.index(':root{\n  --bg:'); b = s.index('}', a) + 1
    s = s[:a] + ':root{\n' + cfg['vars'] + '\n}' + s[b:]
    i = s.index('</style>')
    s = s[:i] + '/* ---------- brand overrides ---------- */\n' + cfg['css'] + BATTLE_CSS + s[i:]
    # header
    a = s.index('  <header class="top">'); b = s.index('</header>', a) + len('</header>')
    hdr = cfg['header'].replace('    <h1>Новогодние игры</h1>', f'    <div class="kp-label">Коммерческое предложение для {cfg["kp_for"]}</div>\n    <h1>Новогодние игры</h1>')
    assert 'kp-label' in hdr
    s = s[:a] + hdr + s[b:]
    rep('<script>\n(function(){', '<script>window.BRAND_GAME=' + json.dumps(cfg['brand_game'], ensure_ascii=False) + ';</script>\n<script>\n(function(){')
    rep('  <p class="ov-hint">Нажмите на игру, чтобы попробовать её и посмотреть пакеты.</p>',
        '  <p class="ov-hint">Нажмите на игру, чтобы попробовать её и посмотреть пакеты.</p>\n\n' + cfg['why'])
    rep('<span class="ic">🧾</span><b>Свой код на каждой покупке</b><small>Упаковка, чек, стакан или карточка</small>', cfg['code_card'])
    rep('Сколько покупок в акции, столько и кодов: каждый уникальный.', cfg['code_line'])
    # games
    a = s.index('const GAMES=['); b = s.index('/* ---------- render overview')
    s = s[:a] + games_js(cfg['games']) + f"const BATTLE_OPTS={json.dumps(cfg['battle'], ensure_ascii=False)};\nconst BATTLE_NOTE={json.dumps(cfg['battle_note'], ensure_ascii=False)};\n\n" + s[b:]
    rep("const OVIMG={drug:'mascot_full.webp',ded:'santa_joy.webp'};", 'const OVIMG=' + json.dumps(cfg['ovimg']) + ';')
    a = s.index('const ADV_PRIZES='); b = s.index(';', a) + 1
    s = s[:a] + 'const ADV_PRIZES=' + json.dumps(cfg['advent'], ensure_ascii=False) + ';' + s[b:]
    rep("31?['🎄','Большой подарок','Главный приз сезона от бренда']", "31?" + json.dumps(cfg['advent_last'], ensure_ascii=False))
    a = s.index('const SC_PRIZES='); b = s.index(';', a) + 1
    s = s[:a] + 'const SC_PRIZES=' + json.dumps(cfg['scratch'], ensure_ascii=False) + ';' + s[b:]
    a = s.index('  const FOODS='); b = s.index(';', a) + 1
    s = s[:a] + '  const FOODS=' + json.dumps(cfg['foods'], ensure_ascii=False) + ';' + s[b:]
    rep("x.fillText(it.bad?'❄️':'🎁',it.x,it.y);", "x.fillText(it.bad?'❄️':(" + json.dumps(cfg['catch']) + "[Math.floor(it.x)%" + str(len(cfg['catch'])) + "]),it.x,it.y);")
    rep('/* ---------- routing ---------- */', BATTLE_JS + '\n/* ---------- routing ---------- */')
    rep('const MOUNT={drug:mountFriend,ded:mountSanta,advent:mountAdvent,elka:mountTree,scratch:mountScratch,catch:mountCatch};',
        'const MOUNT={drug:mountFriend,ded:mountSanta,advent:mountAdvent,elka:mountTree,scratch:mountScratch,catch:mountCatch,battle:mountBattle};')
    rep("const t=(location.hash||'#drug').slice(1);const k=MOUNT[t]?t:'drug';",
        f"const t=(location.hash||'#{cfg['games'][0]['id']}').slice(1);const k=MOUNT[t]&&GAMES.some(g=>g.id===t)?t:'{cfg['games'][0]['id']}';")
    for o, n in cfg.get('texts', []):
        rep(o, n)
    rep('<footer>SHŪ Studio · Астана · 2026</footer>', f'<footer>SHŪ Studio для {cfg["name"]} · ноябрь 2026</footer>')
    a = s.index('https://wa.me/77066767162?text='); b = s.index('"', a)
    from urllib.parse import quote
    s = s[:a] + 'https://wa.me/77066767162?text=' + quote(f'Здравствуйте! Мы посмотрели новогодние игры для {cfg["name"]}, хотим обсудить') + s[b:]
    assert '—' not in s
    return s

CONFIGS = {}

CONFIGS['zenchenko'] = dict(
    name='Зенченко',
    kp_for='«Зенченко»',
    brand_game={'catcher': '🧺', 'toys': ['🥛', '🧀', '🧈', '🥞', '🍶']},
    fonts='https://fonts.googleapis.com/css2?family=Russo+One&family=Jost:wght@400;500;600;700&display=swap&subset=cyrillic',
    vars='''  /* Zenchenko: brand blue from logo #1F5090, light blue, yellow accent from site, constructivist headings */
  --bg:#F4F8FD; --card:#FFFFFF; --ink:#16263D; --muted:#5B6B80; --line:#D6E3F5;
  --berry:#1F5090; --pine:#1F5090; --gold:#F2AC33; --ice:#EEF4FC; --soft:#E3EEFC;
  --red-deep:#163B6C; --stage-a:#FFFFFF; --stage-b:#E6F0FD; --brand:#1F5090;
  --display:"Russo One", "Jost", system-ui, sans-serif;
  --pixel:"Russo One", "Jost", system-ui, sans-serif;
  --body:"Jost", system-ui, -apple-system, "Segoe UI", sans-serif;''',
    css='''body{background:var(--bg);font-size:16px}
.top{background:linear-gradient(160deg,#1F5090,#163B6C);text-align:center;padding:24px 20px;box-shadow:0 6px 0 rgba(31,80,144,.15)}
.top .plate{display:inline-block;background:#fff;border-radius:16px;padding:10px 18px;margin-bottom:12px}
.top .plate img{display:block;width:min(200px,52vw);height:auto}
.top .stars{color:#F2AC33}
h1{text-transform:uppercase;text-shadow:none;letter-spacing:.02em;font-size:clamp(26px,7vw,40px);font-weight:400}
h2,h3{font-weight:400;text-transform:uppercase;letter-spacing:.02em}
h2{color:var(--brand)}h3{color:var(--brand)}
.tab[aria-current="true"]{background:var(--brand);border-color:var(--brand)}
.ribbon{background:#F2AC33;color:#16263D}
.pk h4{font-weight:400}
.pk.best{background:linear-gradient(160deg,#1F5090,#163B6C)}
.cost{color:var(--brand)}
.why{margin-top:16px;background:var(--card);border:2px solid var(--line);border-radius:24px;padding:18px;display:flex;flex-direction:column;gap:10px}
''',
    header='''  <header class="top">
    <span class="stars" aria-hidden="true">★ ❄</span>
    <div class="plate"><img src="assets/brand_logo.svg" alt="Зенченко"></div>
    <h1>Новогодние игры</h1>
    <p class="lead">Новогодний сезон с «Зенченко»: покупатель сканирует код с упаковки молочной продукции или чека фирменного магазина и сразу играет в телефоне. Подготовлено SHŪ Studio.</p>
  </header>''',
    why='''  <section class="why">
    <h2>Почему это подходит «Зенченко»</h2>
    <ul class="list">
      <li><b>Новые фирменные магазины в Астане.</b> Игра приводит покупателей в магазины и даёт повод возвращаться весь декабрь.</li>
      <li><b>Широкий ассортимент.</b> Молоко, кефир, ряженка, сметана, творог, масло: игра мотивирует попробовать новые продукты.</li>
      <li><b>Где будут коды:</b> упаковка продукции, чек фирменного магазина, наклейка или карточка на кассе.</li>
      <li><b>Семейный бренд с историей.</b> Новогодние рецепты и семейный праздник хорошо ложатся на молочную продукцию.</li>
    </ul>
  </section>''',
    code_card='<span class="ic">🥛</span><b>Свой код на каждой покупке</b><small>Упаковка, чек или карточка в фирменном магазине</small>',
    code_line='Сколько упаковок и чеков в акции, столько и кодов: каждый уникальный.',
    ovimg={'ded': 'santa_joy.webp'},
    games=[
        dict(id='advent', em='📅', title='Новогодний календарь рецептов', short='Каждый день рецепт к празднику и сюрприз в фирменном магазине', **{'from': 250000}, term='1 неделя',
             lead='С даты старта акции и до 31 декабря каждый день открывается окошко: новогодний рецепт с продукцией «Зенченко» или сюрприз в фирменном магазине.',
             how='Покупатель сканирует код с покупки и попадает в календарь. Каждый день новое окошко. Что будет в окошках, согласуем на созвоне.',
             extras=[('Рецепт дня от покупателей', '<p>Покупатели присылают свои рецепты, лучшие попадают в календарь. Это живой контент для соцсетей бренда.</p>')],
             pk=[{'n': 'Старт', 'd': 'Окошко каждый день до 31 декабря', 'p': 250000, 't': '1 неделя'}, {'n': 'С рецептами покупателей', 'd': 'Календарь + рецепты от покупателей', 'p': 350000, 't': '1,5 недели', 'best': 1}]),
        dict(id='elka', em='🎄', title='Соберите новогоднюю ёлку', short='Каждая покупка вешает игрушку, готовая ёлка даёт приз', **{'from': 250000}, term='1 неделя',
             lead='Каждый код с упаковки или чека вешает на ёлку новую игрушку. Когда на ёлке все игрушки, загорается звезда и покупатель получает приз.',
             how='Покупатель копит игрушки за покупки. Счётчик показывает, сколько осталось до приза. После приза можно начать новую ёлку.',
             extras=[('Игрушки-продукты', '<p>Каждый вид продукции даёт свою игрушку: молоко, кефир, творог, масло. Чтобы собрать всю ёлку, хочется попробовать весь ассортимент.</p>')],
             pk=[{'n': 'Старт', 'd': 'Ёлка, игрушки за покупки, приз', 'p': 250000, 't': '1 неделя'}, {'n': 'С ассортиментом', 'd': 'Старт + игрушки за разные продукты', 'p': 350000, 't': '1,5 недели', 'best': 1}]),
        dict(id='battle', em='🏪', title='Битва фирменных магазинов', short='Магазины соревнуются, покупатели болеют за свой', **{'from': 300000}, term='1,5 недели',
             lead='Каждый код с покупки добавляет голос магазину, в котором сделана покупка. Магазин-победитель месяца устраивает праздник для своих покупателей.',
             how='Покупатель выбирает свой магазин или он определяется по коду. Табло показывает, кто лидирует. Итоги и призы для победителей задаёт заказчик.',
             extras=[('Районы Астаны', '<p>Соревнуются не магазины, а районы города. Подходит, когда фирменных магазинов станет больше.</p>')],
             pk=[{'n': 'Старт', 'd': 'Битва магазинов с табло', 'p': 300000, 't': '1,5 недели'}, {'n': 'С призами', 'd': 'Старт + розыгрыш среди покупателей магазина-победителя', 'p': 400000, 't': '2 недели', 'best': 1}]),
        dict(id='ded', em='🎅', title='Спасите Деда Мороза', short='Каждый код возвращает подарок в мешок', **{'from': 300000}, term='1,5 недели',
             lead='Подарки потерялись, и мешок Деда Мороза опустел. Каждый код с покупки возвращает подарок. Пройдите 5 этапов, и праздник спасён.',
             how='Каждый новый код открывает следующий этап. Счётчик показывает, на каком этапе игрок и сколько осталось. После 5 этапов покупатель получает приз.',
             extras=[('Мини-игра на каждом этапе', '<p>Например, «поймай подарки». Доплата от 100 000 ₸ за одну игру на все этапы, от 150 000 ₸ за свою игру на каждом этапе.</p>')],
             pk=[{'n': 'Старт', 'd': '5 этапов, уникальные коды по тиражу', 'p': 300000, 't': '1,5 недели'}, {'n': 'С мини-игрой', 'd': 'Старт + одна мини-игра на все этапы', 'p': 400000, 't': '2 недели', 'best': 1}]),
        dict(id='scratch', em='🎟️', title='Стирай и выигрывай', short='Сотрите слой и узнайте приз', **{'from': 250000}, term='1 неделя',
             lead='Покупатель стирает пальцем новогодний слой и видит свой приз: продукт в подарок, скидку в фирменном магазине или промокод.',
             how='Каждый код с покупки даёт одну карточку. Какие призы и как часто они выпадают, задаёт заказчик.',
             extras=[('Собери набор', '<p>На карточках выпадают продукты набора. Собрал все, получил большой приз.</p>')],
             pk=[{'n': 'Старт', 'd': 'Карточка с призом за каждый код', 'p': 250000, 't': '1 неделя'}, {'n': 'С набором', 'd': 'Старт + сбор набора и большой приз', 'p': 350000, 't': '1,5 недели', 'best': 1}]),
        dict(id='catch', em='🥛', title='Поймай молочный подарок', short='Ловите продукты, очки превращаются в промокод', **{'from': 250000}, term='1 неделя',
             lead='Короткая игра на 15 секунд: ловите продукты «Зенченко» и уворачивайтесь от снежинок. Набрали очки, получили промокод.',
             how='Код с покупки даёт попытку. Чем больше очков, тем лучше приз. Призы и пороги очков задаёт заказчик.',
             extras=[('Таблица лидеров', '<p>Лучшие игроки недели видят себя в таблице, а победитель получает главный приз.</p>')],
             pk=[{'n': 'Старт', 'd': 'Игра, очки и промокоды', 'p': 250000, 't': '1 неделя'}, {'n': 'С турниром', 'd': 'Старт + таблица лидеров недели', 'p': 350000, 't': '1,5 недели', 'best': 1}]),
    ],
    battle=[{'e': '🏪', 'n': 'Магазин на Молдагалиева', 'v': 34}, {'e': '🏬', 'n': 'Магазин №2', 'v': 29}, {'e': '🏠', 'n': 'Магазин №3', 'v': 22}],
    battle_note='В демо названия магазинов для примера.',
    advent=[['🥞', 'Сырники к завтраку', 'Рецепт с творогом «Зенченко»'], ['🎂', 'Торт «Наполеон» на сметане', 'Новогодний рецепт'], ['🏷️', 'Скидка в фирменном магазине', 'На молочную продукцию сегодня'], ['🥗', 'Салат с домашней сметаной', 'Рецепт к праздничному столу'], ['🥛', 'Кефир в подарок', 'К любой покупке в фирменном магазине'], ['🧈', 'Новогодняя выпечка на масле', 'Рецепт дня']],
    advent_last=['🎄', 'Новогодний набор', 'Главный подарок сезона от «Зенченко»'],
    scratch=[['🥛', 'Молоко в подарок'], ['🧀', 'Творог в подарок'], ['🏷️', 'Скидка 15% в фирменном магазине'], ['🧈', 'Масло в подарок'], ['🎁', 'Новогодний набор']],
    foods=[{'e': '🥛', 'n': 'молоко', 'v': 20}, {'e': '🧀', 'n': 'творог', 'v': 20}, {'e': '🥞', 'n': 'сырник', 'v': 25}, {'e': '🧈', 'n': 'масло', 'v': 15}],
    catch=['🥛', '🧀', '🧈', '🎁'],
)

CONFIGS['kulikov'] = dict(
    name='Kulikov',
    kp_for='Kulikov',
    brand_game={'catcher': '🛍️', 'toys': ['🍰', '🧁', '🍓', '🍪', '🎂']},
    fonts='https://fonts.googleapis.com/css2?family=Comfortaa:wght@600;700&family=Nunito:wght@400;600;700;800&display=swap&subset=cyrillic',
    vars='''  /* Kulikov: brand purple and lime from kulikov.com, rounded geometric type */
  --bg:#FBF6FC; --card:#FFFFFF; --ink:#2A1033; --muted:#6E5878; --line:#EBDDF0;
  --berry:#9419AC; --pine:#4F7A00; --gold:#93CD0C; --ice:#F6EEF9; --soft:#F3E3F7;
  --red-deep:#60146F; --stage-a:#FFFFFF; --stage-b:#F3E6F8; --brand:#9419AC; --lime:#93CD0C;
  --display:"Comfortaa", "Nunito", system-ui, sans-serif;
  --pixel:"Comfortaa", "Nunito", system-ui, sans-serif;
  --body:"Nunito", system-ui, -apple-system, "Segoe UI", sans-serif;''',
    css='''body{background:var(--bg);font-size:15px}
.top{background:radial-gradient(120% 90% at 80% 0%,#B83CCB,#9419AC 45%,#60146F);text-align:left;padding:24px 20px 26px;box-shadow:0 6px 0 rgba(96,20,111,.18)}
.top .logo{display:block;width:min(200px,55vw);height:auto;margin-bottom:12px}
.top .stars{color:#93CD0C}
h1{text-shadow:none;font-weight:700;font-size:clamp(28px,7.5vw,42px)}
h2{color:var(--brand);font-weight:700}h3{color:var(--brand);font-weight:700}
.btn{background:#93CD0C;color:#1f2a05}
.btn.hot{background:#9419AC;color:#fff}
.btn.alt{background:var(--ice);color:var(--ink)}
.tab[aria-current="true"]{background:var(--brand);border-color:var(--brand)}
.ribbon{background:#93CD0C;color:#1f2a05}
.pk.best{background:linear-gradient(160deg,#9419AC,#60146F)}
.wa{background:#25D366;color:#fff}
.why{margin-top:16px;background:var(--card);border:2px solid var(--line);border-radius:24px;padding:18px;display:flex;flex-direction:column;gap:10px}
''',
    header='''  <header class="top">
    <span class="stars" aria-hidden="true">✦ ❄</span>
    <img class="logo" src="assets/brand_logo.webp" alt="Kulikov">
    <h1>Новогодние игры</h1>
    <p class="lead">Новогодний сезон с Kulikov: покупатель сканирует код с коробки торта, пакета или чека и сразу играет в телефоне. Подготовлено SHŪ Studio.</p>
  </header>''',
    why='''  <section class="why">
    <h2>Почему это подходит Kulikov</h2>
    <ul class="list">
      <li><b>Больше 150 фирменных магазинов</b> в Кыргызстане, Казахстане и России: игра работает во всей сети одновременно, а магазины или города могут соревноваться.</li>
      <li><b>Торты и десерты к празднику.</b> Новый год для Kulikov главный сезон: игра даёт повод выбрать торт именно у вас и вернуться за следующим.</li>
      <li><b>Где будут коды:</b> коробка торта, пакет с десертами, чек, наклейка на упаковке.</li>
      <li><b>Приложение Kulikov.</b> Призы из игры можно связать с кешбэком и предложениями в вашем приложении. Обсудим на созвоне.</li>
    </ul>
  </section>''',
    code_card='<span class="ic">🎂</span><b>Свой код на каждой покупке</b><small>Коробка торта, пакет с десертами или чек</small>',
    code_line='Сколько коробок и чеков в акции, столько и кодов: каждый уникальный.',
    ovimg={'ded': 'santa_joy.webp'},
    games=[
        dict(id='battle', em='🍰', title='Битва тортов', short='Каждая покупка становится голосом за любимый торт', **{'from': 300000}, term='1,5 недели',
             lead='Какой торт главный на Новый год? Каждый код с покупки добавляет голос за любимый торт. В конце сезона торт-победитель получает праздничную акцию.',
             how='Покупатель выбирает торт, за который болеет, и каждый новый код добавляет ему голос. Табло показывает, кто лидирует. Итоги и акцию для победителя задаёт заказчик.',
             extras=[('Битва городов и стран', '<p>Соревнуются города или страны сети: Бишкек, Алматы, Шымкент. Хороший повод для новостей в соцсетях.</p>')],
             pk=[{'n': 'Старт', 'd': 'Битва тортов с табло', 'p': 300000, 't': '1,5 недели'}, {'n': 'С городами', 'd': 'Старт + битва городов сети', 'p': 450000, 't': '2 недели', 'best': 1}]),
        dict(id='scratch', em='🎁', title='Сюрприз в коробке торта', short='Сотрите слой и узнайте приз', **{'from': 250000}, term='1 неделя',
             lead='В каждой коробке торта код. Покупатель стирает пальцем новогодний слой и видит приз: десерт в подарок, скидку или промокод.',
             how='Каждый код с покупки даёт одну карточку. Какие призы и как часто они выпадают, задаёт заказчик.',
             extras=[('Собери набор', '<p>На карточках выпадают части сладкого набора. Собрал все, получил большой торт в подарок.</p>')],
             pk=[{'n': 'Старт', 'd': 'Карточка с призом за каждый код', 'p': 250000, 't': '1 неделя'}, {'n': 'С набором', 'd': 'Старт + сбор набора и большой приз', 'p': 350000, 't': '1,5 недели', 'best': 1}]),
        dict(id='advent', em='📅', title='Сладкий адвент-календарь', short='Окошко с десертным сюрпризом каждый день до 31 декабря', **{'from': 250000}, term='1 неделя',
             lead='С даты старта акции и до 31 декабря каждый день открывается окошко: десерт дня, скидка на торт, сюрприз в магазине. Код с покупки открывает бонусное окошко.',
             how='Покупатель сканирует код с покупки и попадает в календарь. Каждый день новое окошко. Что будет в окошках, согласуем на созвоне.',
             extras=[('Календарь в приложении', '<p>Окошки дают бонусы в приложении Kulikov. Покупатель заходит каждый день и чаще пользуется приложением.</p>')],
             pk=[{'n': 'Старт', 'd': 'Окошко каждый день до 31 декабря', 'p': 250000, 't': '1 неделя'}, {'n': 'С приложением', 'd': 'Календарь + связка с бонусами приложения', 'p': 400000, 't': '1,5 недели', 'best': 1}]),
        dict(id='elka', em='🎄', title='Сладкая ёлка', short='Каждая покупка вешает игрушку, готовая ёлка даёт приз', **{'from': 250000}, term='1 неделя',
             lead='Каждый код с покупки вешает на ёлку новую игрушку. Когда на ёлке все игрушки, загорается звезда и покупатель получает торт или десерт в подарок.',
             how='Покупатель копит игрушки за покупки. Счётчик показывает, сколько осталось до приза. После приза можно начать новую ёлку.',
             extras=[('Игрушки-десерты', '<p>Каждый вид десерта даёт свою игрушку: «Наполеон», «Птичье молоко», «Молочная девочка». Чтобы собрать всю ёлку, хочется попробовать разные торты.</p>')],
             pk=[{'n': 'Старт', 'd': 'Ёлка, игрушки за покупки, приз', 'p': 250000, 't': '1 неделя'}, {'n': 'С десертами', 'd': 'Старт + игрушки за разные десерты', 'p': 350000, 't': '1,5 недели', 'best': 1}]),
        dict(id='catch', em='🍰', title='Поймай десерт', short='Ловите десерты, очки превращаются в промокод', **{'from': 250000}, term='1 неделя',
             lead='Короткая игра на 15 секунд: ловите десерты Kulikov и уворачивайтесь от снежинок. Набрали очки, получили промокод.',
             how='Код с покупки даёт попытку. Чем больше очков, тем лучше приз. Призы и пороги очков задаёт заказчик.',
             extras=[('Таблица лидеров', '<p>Лучшие игроки недели видят себя в таблице, а победитель получает торт в подарок.</p>')],
             pk=[{'n': 'Старт', 'd': 'Игра, очки и промокоды', 'p': 250000, 't': '1 неделя'}, {'n': 'С турниром', 'd': 'Старт + таблица лидеров недели', 'p': 350000, 't': '1,5 недели', 'best': 1}]),
        dict(id='ded', em='🎅', title='Спасите Деда Мороза', short='Каждый код возвращает подарок в мешок', **{'from': 300000}, term='1,5 недели',
             lead='Подарки потерялись, и мешок Деда Мороза опустел. Каждый код с покупки возвращает подарок. Пройдите 5 этапов, и праздник спасён.',
             how='Каждый новый код открывает следующий этап. Счётчик показывает, на каком этапе игрок и сколько осталось. После 5 этапов покупатель получает приз.',
             extras=[('Мини-игра на каждом этапе', '<p>Например, «поймай десерт». Доплата от 100 000 ₸ за одну игру на все этапы, от 150 000 ₸ за свою игру на каждом этапе.</p>')],
             pk=[{'n': 'Старт', 'd': '5 этапов, уникальные коды по тиражу', 'p': 300000, 't': '1,5 недели'}, {'n': 'С мини-игрой', 'd': 'Старт + одна мини-игра на все этапы', 'p': 400000, 't': '2 недели', 'best': 1}]),
    ],
    battle=[{'e': '🍰', 'n': 'Наполеон', 'v': 31}, {'e': '🎂', 'n': 'Птичье молоко', 'v': 36}, {'e': '🍓', 'n': 'Молочная девочка', 'v': 27}],
    battle_note='В демо торты и проценты для примера.',
    advent=[['🍰', 'Десерт дня', 'Скидка на десерт сегодня'], ['🎂', 'Скидка на торт', 'К новогоднему столу'], ['☕', 'Напиток к десерту', 'В подарок в магазине'], ['🍪', 'Новинка сезона', 'Попробуйте первым'], ['✨', 'Бонусы ×2', 'В приложении Kulikov'], ['🎁', 'Сюрприз в магазине', 'Спросите у продавца']],
    advent_last=['🎄', 'Новогодний торт', 'Главный подарок сезона от Kulikov'],
    scratch=[['🍰', 'Десерт в подарок'], ['🎂', 'Скидка 15% на торт'], ['☕', 'Напиток в подарок'], ['✨', 'Бонусы в приложении'], ['🎁', 'Сладкий набор']],
    foods=[{'e': '🍰', 'n': 'торт', 'v': 25}, {'e': '🧁', 'n': 'капкейк', 'v': 15}, {'e': '🍪', 'n': 'печенье', 'v': 20}, {'e': '🍓', 'n': 'клубника', 'v': 20}],
    catch=['🍰', '🧁', '🍪', '🎁'],
)

if __name__ == '__main__':
    brand = sys.argv[1]
    cfg = CONFIGS[brand]
    out = ROOT / brand
    (out / 'assets').mkdir(parents=True, exist_ok=True)
    for f in (ROOT / 'shu-newyear' / 'assets').iterdir():
        shutil.copy(f, out / 'assets' / f.name)
    (out / 'index.html').write_text(build(cfg))
    print('ok', out / 'index.html')
