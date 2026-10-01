"""Dependency-free static HTML generator. Global business data live in config/site.json."""
import argparse, json, html, shutil
from pathlib import Path
from datetime import date
from urllib.parse import urlencode, quote
from seo import LABELS, enhance, structured_data, inquiry_template

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--config', default=str(ROOT/'config/site.json'))
parser.add_argument('--output', default=str(ROOT/'dist'))
args = parser.parse_args()
C = json.loads(Path(args.config).read_text(encoding='utf-8'))
OUT = Path(args.output)
OUT.mkdir(parents=True, exist_ok=True)
E = html.escape
R = C['rates']
minimum_text = f"Минимальная партия: {C['conditions']['minimumBatch']} шт." if C['conditions']['minimumBatch'] else 'Уточните возможность приема вашей партии по телефону или почте.'
cutoff_text = f"Задания принимаются до {C['conditions']['cutoff']}." if C['conditions']['cutoff'] else 'До первой отгрузки уточните, до какого часа передавать заказы, когда они уезжают и как склад работает в выходные.'
processing_text = f"Срок обработки: {C['conditions']['processingTime']}." if C['conditions']['processingTime'] else 'Срок обработки согласуется по объему и заданию.'
def rub(n): return f'{n:,.2f}'.rstrip('0').rstrip('.').replace(',', ' ').replace('.', ',') + ' ₽'
def link(href, text, cls=''): return f'<a class="{cls}" href="{href}">{text}</a>'
def call_href(phone):
    digits=''.join(c for c in phone if c.isdigit())
    if len(digits)==11 and digits.startswith('8'): digits='7'+digits[1:]
    if len(digits)!=11 or not digits.startswith('7'): raise ValueError('Invalid contact number')
    return 'tel:+'+digits
def contact_cell(name, value):
    if 'телефон' in name.lower() and value: return link(call_href(value),E(value))
    if name=='Электронная почта' and value: return link('mailto:'+E(value),E(value))
    return E(str(value))
def button(text='Обсудить мою задачу', href='#request', secondary=False): return link(href,text, 'button secondary' if secondary else 'button')
def label(text): return f'<p class="eyebrow">{text}</p>'
def section(title, body, intro='', cls=''):
    return f'<section class="section {cls}"><div class="section-head"><h2>{title}</h2>{f"<p>{intro}</p>" if intro else ""}</div>{body}</section>'
def cards(items):
    return '<div class="cards">'+''.join(f'<article class="card"><span class="index">{i+1:02}</span><h3>{h}</h3><p>{p}</p>{link(u,"Подробнее <span aria-hidden=\"true\">↗</span>","text-link") if u else ""}</article>' for i,(h,p,u) in enumerate(items))+'</div>'
def steps(items):
    return '<ol class="steps">'+''.join(f'<li><span>{i+1:02}</span><div><h3>{h}</h3><p>{p}</p></div></li>' for i,(h,p) in enumerate(items))+'</ol>'
def faq(items): return '<div class="faq">'+''.join(f'<details><summary>{q}</summary><p>{a}</p></details>' for q,a in items)+'</div>'
def photo(filename, alt, caption, prominent=False):
    loading = 'eager' if prominent else 'lazy'
    priority = ' fetchpriority="high"' if prominent else ''
    return f'<figure class="story-image"><img src="/assets/{filename}.webp" alt="{E(alt)}" width="1536" height="1024" loading="{loading}"{priority} decoding="async"><figcaption>Иллюстрация. {E(caption)}</figcaption></figure>'
def notice(text=None): return f'<p class="notice">{E(text or C["rateNote"])}</p>' if C['demo'] else ''
def hero(kicker,title,intro,aside='',cta_text='Обсудить мою задачу',cta_href='#request'):
    cls='page-hero with-art' if aside else 'page-hero'
    return f'<section class="{cls}"><div>{label(kicker)}<h1>{title}</h1><p class="lead">{intro}</p><div class="actions">{button(cta_text,cta_href)}</div></div>{aside}</section>'
def lead_form(service='party'):
    prompts = {
        'general': ('Расскажите о товаре<br>и вашей задаче', 'Напишите, какую работу хотите передать складу, что за товар и какой примерно объем. Укажите нужную дату, если она уже известна. Остальные параметры можно уточнить в разговоре.'),
        'party': ('Начните с товара<br>и нужной даты', 'Напишите, что за товар, сколько единиц и к какой дате нужна подготовка. Если объем или дата пока неизвестны, так и укажите. Готовый список или фото можно приложить к письму.'),
        'fbs': ('Расскажите о товаре<br>и потоке заказов', 'Начните с товара, примерного числа заказов в день и желаемой даты перехода. Если переносите запас от другого оператора, укажите это в письме.'),
        'pack': ('Пришлите фото товара<br>и пример упаковки', 'Укажите количество единиц и нужные операции. Если требования к отправлению или образец этикетки уже есть, приложите их к письму.'),
        'delivery': ('Куда и когда<br>нужно отвезти товар?', 'Укажите склад назначения, дату, количество мест, размеры и вес. По этим данным обсудим маршрут и стоимость перевозки.'),
        'storage': ('Обсудим размещение<br>вашего товара', 'Для начала нужны категория товара, размеры, вес и объем запаса. Укажите, планируются поставки на маркетплейсы или сборка отдельных заказов, в том числе из интернет-магазина.'),
        'price': ('Обсудим расчет<br>по вашему заданию', 'Для начала напишите, какой товар и объем нужно обработать, что уже готово и к какой дате нужна отгрузка. Если точных размеров или состава упаковки пока нет, укажите это.')
    }
    heading, details = prompts[service]
    subjects = {'general':'Обсуждение работ с товаром', 'party':'Подготовка партии', 'fbs':'Сборка FBS-заказов', 'pack':'Упаковка и маркировка', 'delivery':'Доставка', 'storage':'Хранение и сборка заказов', 'price':'Запрос расчета'}
    quantity_label = 'Заказов в день, примерно' if service=='fbs' else 'Примерный объем'
    task = '' if service=='general' else subjects[service]
    draft_body = 'Здравствуйте! Хочу обсудить работу с товаром.\n\nЗадача: '+task+'\nКанал продаж или площадка, если уже выбраны: \nТовар: \n'+quantity_label+': \nНужная дата: \n\nНеизвестные параметры можно оставить незаполненными.'
    if service == 'delivery':
        draft_body = 'Здравствуйте! Хочу обсудить доставку партии на маркетплейс.\n\nПлощадка и склад назначения: \nНужная дата: \nГруз (товар, число коробов или паллет): \nГде находится партия: \nРазмеры и вес, если известны: \nНужна ли дополнительная подготовка: \n\nНеизвестные параметры можно уточнить в разговоре.'
    if C['contact']['phone'] and C['contact']['email']:
        phone=E(C['contact']['phone'])
        email=E(C['contact']['email'])
        draft_href='mailto:'+C['contact']['email']+'?'+urlencode({'subject':C['brand']+': '+subjects[service], 'body':draft_body},quote_via=quote)
        return f'<section class="lead-section" id="request"><div><p class="eyebrow">Связаться со складом</p><h2>{heading}</h2><p>{details}</p></div><div class="contact-actions">{button("Позвонить: "+phone,call_href(C["contact"]["phone"]))}{link(E(draft_href),"Написать: "+email,"button secondary")}<p class="email-note">Откроется черновик в почтовой программе. Вы сами дополните и отправите письмо.</p><p>Перед приездом на склад согласуйте время по телефону.</p></div></section>'
    return '''<section class="lead-section" id="request"><div><p class="eyebrow">Начнем с вашей задачи</p><h2>Расскажите о вашей партии</h2><p>Укажите товар и объем. Этих данных достаточно, чтобы начать обсуждение состава работ.</p><span class="form-note">Демо: данные не отправляются. Не вводите личные контакты.</span></div><form class="lead-form" novalidate><label>Что нужно сделать<select name="service"><option>Подготовить партию на склад маркетплейса</option><option>Хранить товар и собирать FBS-заказы</option><option>Упаковать или промаркировать товар</option></select></label><div class="form-row"><label>Товар<input name="product" placeholder="Например, футболки" maxlength="120" required></label><label>Объем, шт.<input name="quantity" type="number" min="1" max="1000000" step="1" placeholder="500" required></label></div><button class="button" type="submit" disabled>Посмотреть пример заявки <span aria-hidden="true">↗</span></button><p class="form-result" role="status" aria-live="polite"></p><noscript><p>Для демонстрации формы включите JavaScript. Тарифы и состав услуг доступны без него.</p></noscript></form></section>'''

NAV=[('/', 'Главная'),('/tarify/','Тарифы'),('/fbs/','FBS'),('/podgotovka-postavok/','Подготовка поставок'),('/dostavka/','Доставка'),('/sklad/','Склад'),('/kontakty/','Контакты')]
PAGES={}
def add(path,title,description,h1,body): PAGES[path]={'title':title,'description':description,'h1':h1,'body':body}

# A functional parcel workflow occupies the hero until the illustrative asset is ready.
hero_visual='''<div class="hero-art"><img src="/assets/parcels.webp" alt="Иллюстрация упаковки: коробки и пакет для отправки" width="1200" height="800" fetchpriority="high"><div class="route-note"><span class="route-label">От приемки до подготовки к отправке</span><div><span>Приемка</span><b aria-hidden="true">→</b><span>Подготовка</span><b aria-hidden="true">→</b><span>Отгрузка</span></div></div><span class="image-caption">Иллюстрация</span></div>'''
home=f'''<section class="home-hero"><div class="hero-copy">{label('Для маркетплейсов, интернет-магазинов и брендов')}<h1>Фулфилмент<br>в Ростове-<wbr><span class="city-tail">на-Дону.</span></h1><p class="lead">Храним товары, готовим партии и собираем заказы для маркетплейсов и интернет-магазинов. Передайте нам упаковку, маркировку и подготовку к отправке. Состав работ, стоимость и сроки согласуем под вашу задачу.</p><div class="actions">{button()}{link(call_href(C['contact']['phone']),'Позвонить','text-link')}</div></div>{hero_visual}<div class="hero-location"><span>Наш склад</span>{link("/kontakty/",E(C["contact"]["address"]))}</div></section>
<div class="service-strip"><span>Приемка и хранение</span><span>Упаковка и маркировка</span><span>Сборка заказов</span><span>{link('/dostavka/','Доставка на маркетплейсы')}</span></div>
<section class="section" id="services"><div class="section-head"><h2>Что вам нужно сейчас</h2><p>Выберите ситуацию. Подробности работ и подготовки товара есть на страницах услуг.</p></div><div class="situation-list">
<article><h3>Готовите первую поставку</h3><div><p>Нужно отправить партию на склад маркетплейса. Посмотрите, какие работы входят в подготовку, и укажите площадку, для которой готовите товар.</p>{link('/podgotovka-postavok/','Подготовка первой партии','text-link')}</div></article>
<article><h3>Собираете FBS-заказы сами</h3><div><p>Хотите передать хранение, упаковку и сборку заказов складу. До начала работы важно согласовать передачу заданий и график отгрузки.</p>{link('/fbs/','Хранение и сборка FBS','text-link')}</div></article>
<article><h3>Заказы идут из<br>интернет-магазина</h3><div><p>Нужно хранить запас и собирать посылки по заказам с вашего сайта. Обсудим упаковку, передачу заданий и подготовку отправлений для выбранного перевозчика.</p>{link('/sklad/#internet-magaziny','Хранение и сборка для магазина','text-link')}</div></article>
<article class="delivery-situation"><h3>Партия готова.<br>Нужна доставка.</h3><div><p>Товар уже упакован и промаркирован. Обсудим доставку коробов или паллет на склад маркетплейса. Для начала нужны направление, дата и параметры груза.</p>{link('/dostavka/','Доставка на маркетплейсы из Ростова','text-link')}</div></article>
<article><h3>Планируете сменить склад</h3><div><p>До перемещения товара нужно сверить остатки и незакрытые заказы. Сообщите, где находится запас и когда нужен переход.</p>{link('/sklad/#request','Обсудить переход','text-link')}</div></article>
<article><h3>Нужна только упаковка<br>или маркировка</h3><div><p>Укажите, что уже сделано и какую обработку нужно выполнить. Отдельные операции можно согласовать без полной подготовки поставки.</p>{link('/upakovka-markirovka/','Выбрать операции','text-link')}</div></article>
</div></section>'''
home+=section('От первого сообщения<br>до передачи товара',steps([('Опишите вашу задачу','Напишите, что за товар, примерное количество и нужную дату. Неизвестные параметры можно уточнить в разговоре.'),('Согласуем состав работ','До приема товара определим нужные операции, стоимость работ и материалов. Доставка и срок подготовки также требуют согласования.'),('Подготовьте товар к приемке','После согласования задания договоримся о времени приезда. Для сверки партии нужен список артикулов и количества.')]),'Вы передаете товар и задание. Склад выполняет согласованную подготовку партии или сборку отдельных заказов.')
home+=photo('packing','Проверка упаковки и нанесение этикетки на короб','Проверка упаковки перед отправкой')
home+=section('Что согласовать<br>перед передачей товара', '<div class="trust-grid"><div class="trust-big"><span class="index">До первой поставки</span><h3>Как будет учитываться<br>ваша партия</h3><p>Обсудите документы приемки, способ сверки остатков и порядок возврата товара. Условия ответственности проверьте в договоре до передачи партии.</p>'+link('/sklad/','Что уточнить перед стартом ↗','text-link')+'</div><div class="trust-list"><article><h3>Приемка по артикулам</h3><p>Каким документом подтверждаются количество и состояние принятого товара.</p></article><article><h3>Подтверждение отгрузки</h3><p>Как узнать, что партия или заказ переданы, и получить подтверждение.</p></article><article><h3>Остатки и возвраты</h3><p>Как часто сверяется запас и где учитывается товар, который вернул покупатель.</p></article></div></div>')
home+=section('Частые вопросы',faq([('Работаете только с Озон и ВБ?','Нет. Принимаем задачи для других маркетплейсов, интернет-магазинов и брендов. Укажите площадку или канал продаж: по ним определим требования к упаковке, заданиям и передаче товара.'),('Можно передать только упаковку партии?','Да. В задании можно выделить отдельные операции: приемку, упаковку, маркировку или подготовку поставки. Состав работ и ограничения согласовываются до приема товара.'),('Чем FBS отличается от подготовки поставки?','При FBS (ФБС) товар хранится у нас, а заказы собираются по мере продаж на маркетплейсе. Ozon (Озон) и Wildberries (ВБ) работают по такой схеме. При подготовке FBO/FBW партия отправляется на склад самого маркетплейса для дальнейшего хранения и обработки.'),('Что нужно для расчета?','Категория и размеры товара, количество единиц и артикулов, схема работы, требования к упаковке и направление доставки. Для FBS также нужен ожидаемый объем заказов и запас на хранении.'),('Есть ли минимальная партия?','Уточните возможность приема вашей партии по телефону или почте. В калькуляторе можно проверить разные объемы, но расчет не подтверждает прием партии в работу.')] ))
home+=lead_form('general')
add('/',f'Фулфилмент в Ростове-на-Дону | {C["brand"]}','Хранение, упаковка и сборка заказов для маркетплейсов, интернет-магазинов и брендов. Обсудите состав работ и стоимость своей партии.','Фулфилмент в Ростове-на-Дону',home)

calc=f'''<section class="section" id="calculator"><div class="section-head"><h2>Посчитайте свой объем</h2><p>Выберите подготовку партии или FBS и укажите объем. Сумма рассчитана по демонстрационным ставкам.</p></div>{notice()}<div class="calculator"><form id="calc-form"><fieldset class="mode-switch"><legend class="sr-only">Схема работы</legend><label><input type="radio" name="mode" value="fbo" checked><span>Подготовка партии</span></label><label><input type="radio" name="mode" value="fbs"><span>FBS за месяц</span></label></fieldset><div class="calc-fields"><label><span id="quantity-label">Товаров в партии, шт.</span><input id="calc-quantity" type="number" min="1" max="1000000" step="1" value="{C['defaults']['units']}" required></label><label id="boxes-field">Коробов на доставку<input id="calc-boxes" type="number" min="0" max="100000" step="1" value="{C['defaults']['boxes']}" required></label><label>Объем хранения, м³<input id="calc-volume" type="number" min="0" max="10000" step="0.1" value="0" required></label><label>Дней хранения<input id="calc-days" type="number" min="0" max="365" step="1" value="0" required></label></div><p class="small" id="calc-condition">Один товар в индивидуальном пакете и одна этикетка на единицу. Типовой пример без специальных операций.</p><p id="calc-error" class="error" role="alert"></p></form><div class="calc-result" aria-live="polite"><p class="eyebrow">Демонстрационный расчет</p><div id="calc-lines" hidden></div><div class="calc-total"><span>Сумма по выбранным параметрам</span><strong id="calc-total">{rub((R['receive']+R['label']+R['pack']+R['material'])*C['defaults']['units']+R['boxDelivery']*C['defaults']['boxes'])}</strong></div><p class="small" id="calc-exclusions">Не включены забор у поставщика и нестандартные работы. Хранение учитывается по введенным объему и сроку. Налоговые условия уточняются при согласовании цены.</p><a href="#request" class="button">Обсудить состав работ</a></div></div><noscript><p>Для интерактивного расчета включите JavaScript.</p></noscript></section>'''
tariffs=hero('Тарифы','Посчитайте поставку<br>под свой объем.','Одна и та же партия может требовать только этикеток или полной переупаковки. Калькулятор показывает типовой пример. Стоимость ваших работ и материалов уточним по составу товара.',cta_text='Посмотреть пример расчета',cta_href='#calculator')+calc+lead_form('price')
tariffs=tariffs.replace('<p class="notice">', '<p class="small">В калькуляторе показаны примеры подготовки партии и FBS. Для интернет-магазина состав обработки и доставки рассчитывается по отдельному заданию.</p><p class="notice">',1)
add('/tarify/',f'Тарифы на фулфилмент в Ростове-на-Дону | {C["brand"]}','Калькулятор примерной стоимости подготовки партии и обработки FBS-заказов.','Посчитайте поставку под свой объем.',tariffs)

fbs=hero('Хранение и сборка заказов','Ваш запас на складе.<br>Каждый заказ в работе.','При работе по FBS (ФБС) запас хранится у нас. Собираем заказы для маркетплейсов, в том числе Озон и Wildberries: подбираем товар, упаковываем и готовим к передаче выбранной площадке.',aside=photo('fbs','Аккуратно размещенные товары и пакеты на стеллаже','Организованное хранение запаса для FBS',prominent=True),cta_text='Позвонить',cta_href=call_href(C['contact']['phone']))
fbs+=section('От поступления товара до отправки заказа',steps([('Принимаем товар на хранение','Пересчитываем товар по артикулам. Способ передачи заданий и сверки остатков выбираем до начала сборки.'),('Проверяем задание','Для сборки нужны состав заказа и этикетка. Заранее определяем, до какого времени нужно передать задание, чтобы успеть к отгрузке.'),('Собираем заказ','Подбираем нужный артикул и количество, упаковываем товар и наносим этикетку заказа.'),('Передаем заказ площадке','Порядок подтверждения передачи согласуем заранее. Возвращенный товар нужно проверить перед повторной продажей.')]))
fbs+=section('До первого FBS-заказа',cards([('График работы','До первой отгрузки уточните, до какого часа передавать заказы, когда они уезжают и как склад работает в выходные.',None),('Учет остатков','Согласуйте формат отчета и частоту обновления. Возможность интеграции с кабинетом продавца уточняется отдельно.',None),('Возвраты','Определите, кто проверяет возвращенный товар и принимает решение о повторной продаже. Поврежденную упаковку может потребоваться заменить.',None)]))
fbs+=section('Когда подходит FBS','<div class="editorial"><p>Рассмотрите FBS, если хотите хранить запас вне склада маркетплейса и передать сборку заказов подрядчику. До переезда товара сопоставьте свой поток заказов с графиком сборки и передачи.</p><p>Если товар уже у другого оператора, начните со сверки остатков и незакрытых заказов. Дату переезда нужно выбрать так, чтобы было понятно, какой склад собирает каждый заказ.</p></div>')
fbs+=f'<div class="section"><div class="callout"><p>Посчитайте обработку заказов за месяц.</p>{button("Рассчитать FBS", "/tarify/?mode=fbs#calculator")}</div></div>'+lead_form('fbs')
add('/fbs/',f'FBS-фулфилмент в Ростове-на-Дону | {C["brand"]}','Хранение товара, сборка FBS-заказов, упаковка и передача на маркетплейсы. Состав работ и учет остатков.','Ваш запас на складе. Каждый заказ в работе.',fbs)

prep=hero('Подготовка поставок на маркетплейсы','Партия готова<br>к передаче на маркетплейс.','Пересчитываем товар, упаковываем и наносим этикетки. Собираем короба или паллеты для поставки на склад маркетплейса по согласованному заданию. Требования зависят от выбранной площадки и схемы поставки.')
prep+=section('Что происходит с партией',steps([('Сверяем товар','Сопоставляем количество и артикулы с документами. Видимые повреждения и расхождения выделяем отдельно.'),('Проверяем и упаковываем','Проверяем, комплектуем, упаковываем и наносим согласованные этикетки.'),('Собираем поставку','Распределяем товар по коробам или паллетам. Проверяем, совпадают ли содержимое и этикетки.'),('Готовим к отгрузке','Согласовываем склад назначения, слот и документы. Заранее определяем, чем будет подтверждаться передача груза.')]))
prep+=photo('shipment','Группа коробов на паллете, готовая к отправке','Собранная партия перед передачей на маркетплейс')
prep+=section('Для расчета подготовьте',cards([('Данные о товаре','Категория, количество, число артикулов, габариты и вес единицы.',None),('Задание на подготовку','Вид упаковки, глубина проверки, этикетки и необходимость формирования наборов.',None),('Данные о поставке','Площадка и склад назначения, плановая дата, число коробов или паллет.',None)]))
prep+=section('Примеры подготовки для Ozon и Wildberries','<div class="model-grid"><article class="card"><span class="pill">Ozon · FBO</span><h3>Подготовка по заданию поставки</h3><p>Состав партии, этикетки и документы сверяются с актуальными требованиями выбранного склада Ozon.</p></article><article class="card"><span class="pill">Wildberries · FBW</span><h3>Подготовка к отгрузке на WB</h3><p>Товарная и транспортная упаковка, маркировка коробов и паллет проверяются для конкретной поставки.</p></article></div>','Для другой площадки укажите ее название и требования к поставке. Состав подготовки и место передачи товара согласуем до приема партии.')+lead_form('party')
add('/podgotovka-postavok/',f'Подготовка поставок на маркетплейсы в Ростове | {C["brand"]}','Приемка, пересчет, проверка, упаковка и маркировка партий для маркетплейсов. Подготовка коробов и паллет в Ростове-на-Дону.','Партия готова к передаче на маркетплейс.',prep)

pack=hero('Упаковка и маркировка','Упаковка под товар.<br>Этикетка по заданию.','Упакуем товары для маркетплейса или интернет-магазина, наклеим этикетки и соберем наборы по вашему заданию. Можно заказать отдельную операцию или подготовку всей партии.',cta_text='Обсудить упаковку',cta_href='#request')
pack+=section('Выберите состав работ',cards([('Индивидуальная упаковка','Пакет, коробка или дополнительная защита. Материал и размеры выбираются под товар и требования к отправлению.',None),('Стикеровка товара','Печатаем и наклеиваем этикетки. Пришлите файл для печати и укажите, где разместить этикетку на товаре.',None),('Комплектация и вложения','Собираем товары в наборы, добавляем инструкции и вложения. До начала работы нужно утвердить состав каждого комплекта.',None),('Переупаковка','Проверяем состояние товара и заменяем поврежденную или неподходящую упаковку.',None)]))
pack+=photo('packing','Проверка коробки перед упаковкой и маркировкой','Пример работы с упаковкой и этикеткой')
pack+=section('Сначала согласуйте образец упаковки','<div class="editorial"><p>Для нестандартной упаковки сначала согласуйте образец: материал, положение этикетки, вложения и порядок фиксации. Он поможет одинаково обработать всю партию.</p><p>Нанесение готового кода маркировки и операции в системе Честный знак являются разными задачами. Их состав и доступность нужно согласовать отдельно.</p></div>')
pack+=section('Проверка товара',faq([('Что означает проверка на видимый брак?','Осмотр доступных поверхностей по согласованным признакам. Он не заменяет проверку работоспособности, лабораторную проверку или экспертизу.'),('Можно заказать подробную проверку?','Сначала нужно описать критерии: размеры, швы, комплектацию или работу устройства. Возможность и цену такой проверки определяют по заданию.'),('Материалы входят в работу?','Материал подбирается под товар. Его тип, размер и стоимость согласуются отдельно от упаковочной операции.')]))+lead_form('pack')
add('/upakovka-markirovka/',f'Упаковка и маркировка товаров в Ростове-на-Дону | {C["brand"]}','Упаковка, стикеровка, комплектация наборов и переупаковка товаров для маркетплейсов и интернет-магазинов. Состав работ и материалов.','Упаковка под товар. Этикетка по заданию.',pack)

delivery=hero('Доставка на маркетплейсы','Отгрузка начинается<br>с правильной подготовки.','Доставка подготовленных коробов, паллет и FBS-заказов на маркетплейсы, в том числе Ozon (Озон) и Wildberries (ВБ). Укажите площадку и пункт назначения. Маршрут, дату и стоимость согласуем по параметрам груза.',cta_text='Обсудить доставку',cta_href='#request')
delivery+=section('Два вида отправлений',cards([('Короба и паллеты','Подготовленные партии для склада маркетплейса. Для расчета нужны размеры, вес, число мест и направление.','/podgotovka-postavok/'),('Заказы FBS','Отдельные отправления, собранные по заказам покупателей. До начала работы уточните пункт приема заказов и крайнее время их передачи.','/fbs/')]))
delivery+=section('Что проверить перед выездом',steps([('Направление и дата','Адрес склада или пункта приема, способ поставки и доступность приема.'),('Параметры груза','Количество коробов или паллет, размеры, вес и ограничения перевозки.'),('Этикетки и документы','Соответствие грузовых мест поставке, маркировка и необходимые документы.'),('Порядок подтверждения','Какие документы или статусы будут доступны после передачи и что делать при отказе в приемке.')]))
delivery+=photo('shipment','Подготовленные к перевозке короба на паллете','Партия после упаковки и комплектации')
delivery+=section('Направления и график','<div class="callout"><h3>Согласуются для вашей поставки</h3><p>Назовите точный склад или пункт приема и нужную дату. Перед отправкой подтвердите маршрут и время сдачи груза. Без этих данных стоимость доставки будет неполной.</p>'+button('Обсудить доставку','#request')+'</div>')+lead_form('delivery')
add('/dostavka/',f'Доставка на маркетплейсы из Ростова-на-Дону | {C["brand"]}','Доставка коробов, паллет и FBS-отправлений на маркетплейсы. Параметры груза, подготовка документов и согласование направления.','Отгрузка начинается с правильной подготовки.',delivery)

warehouse=hero('Склад и условия работы','Понятно, где товар.<br>Понятно, что с ним.','Хранение товара для маркетплейсов, интернет-магазинов и брендов. Обсудим размещение запаса, учет остатков и подготовку заказов к передаче. Условия зависят от товара и вашего порядка отгрузок.',cta_text='Обсудить хранение',cta_href='#request')
warehouse+=f'<section class="section" id="internet-magaziny"><div class="section-head"><h2>Заказы вашего<br>интернет-магазина</h2><p>Складскую обработку можно передать нам, даже если продажи идут через собственный сайт.</p></div><div class="editorial"><p>Размещаем товар, подбираем позиции по заданию и упаковываем заказ. До начала работы согласуем, как получать заказы и сведения об остатках, а также как готовить посылки к передаче выбранному перевозчику.</p><p>Укажите, где оформляются заказы и какой службой отправляете посылки. Подключение к системе магазина и доставка покупателю обсуждаются отдельно.</p>{button("Обсудить заказы магазина", "#request")}</div></section>'
warehouse+=section('Что проверить до передачи товара',cards([('Сам склад','Фактический адрес, условия размещения вашего товара, доступ на разгрузку и возможность посещения.',None),('Приемку и учет','Как сверяются артикулы и количество, фиксируется состояние партии и ведутся остатки.',None),('Доступ к информации','В каком формате предоставляются сведения об операциях, остатках и возвратах.',None),('Ответственность сторон','Как рассматривается претензия, чем подтверждается стоимость товара и какие условия содержит договор.',None)]))
warehouse+=section('Если обнаружено расхождение',steps([('Зафиксировать факт','Указать поставку, артикул, количество и характер расхождения. Сохранить доступные документы и материалы.'),('Сверить операции','Сопоставить приемку, задания, отгрузки и возвраты. Определить, на каком этапе возник вопрос.'),('Согласовать решение','Применить условия договора. По результатам сверки определить, нужно ли исправить учет, повторить обработку или рассмотреть возмещение по договору.')]))
warehouse+=section('Сведения о складе',f'<div class="warehouse-placeholder"><span class="index">Адрес склада</span><h3>{E(C["contact"]["address"])}</h3><p>Перед поездкой позвоните: согласуйте время, порядок въезда и разгрузки. Номер склада указан в адресе.</p></div>')
warehouse+=section('Частые вопросы о сохранности',faq([('Можно ли посетить склад?','Адрес и телефоны указаны на странице контактов. Перед поездкой согласуйте возможность и время посещения.'),('Входит ли страхование в расчет?','В демонстрационный расчет страхование не включено. Его наличие и условия нужно уточнить отдельно. Если требуется страховое покрытие, проверьте полис и исключения до передачи товара.'),('FBS гарантирует сохранность запаса?','Схема FBS определяет, где хранится товар и как собираются заказы. Сама по себе она не гарантирует защиту от происшествий. Значение имеют фактические условия хранения и договор.')]))+lead_form('storage')
add('/sklad/',f'Склад фулфилмента и условия хранения в Ростове | {C["brand"]}','Приемка, учет остатков и порядок разбора расхождений. Что проверить перед передачей товара на склад фулфилмента.','Понятно, где товар. Понятно, что с ним.',warehouse)

contact_items=[('Город',C['city']),('Адрес склада',C['contact']['address']),('Основной телефон',C['contact']['phone']),('Дополнительный телефон',C['contact']['phone2']),('Электронная почта',C['contact']['email'])]
if C['contact']['hours']: contact_items.append(('Время работы',C['contact']['hours']))
contacts=hero('Контакты','Контакты склада<br>в Ростове-на-Дону','Расскажите, какой товар и объем планируете передать. Перед приездом на склад согласуйте время по телефону.',cta_text='Позвонить',cta_href=call_href(C['contact']['phone']))
contacts+=section('Как связаться','<dl class="contact-list">'+''.join(f'<div><dt>{n}</dt><dd>{contact_cell(n,v)}</dd></div>' for n,v in contact_items)+'</dl>')
add('/kontakty/',f'Контакты фулфилмента в Ростове-на-Дону | {C["brand"]}',f'Телефоны, почта и адрес склада: {C["contact"]["address"]}.','Контакты склада в Ростове-на-Дону',contacts)

def render(path,p):
    nav=''.join(link(u,n,'active' if path==u else '') for u,n in NAV)
    footerlinks=''.join(link(u,n) for u,n in NAV+[("/upakovka-markirovka/","Упаковка и маркировка")])
    footer_contact=' '.join([link(call_href(C['contact'][key]),E(C['contact'][key])) for key in ('phone','phone2')]+[link('mailto:'+E(C['contact']['email']),E(C['contact']['email'])),f'<span>{E(C["contact"]["address"])}</span>'])
    cfg=json.dumps(C,ensure_ascii=False).replace('</','<\\/')
    robots='noindex, nofollow, noarchive' if C['demo'] else 'index, follow'
    structured=structured_data(C,path,p)
    demo='<div class="demo-bar"><span>Демонстрационный сайт</span><span>Тарифы и условия будут уточнены перед запуском</span></div>' if C['demo'] else ''
    crumb='' if path=='/' else '<nav class="breadcrumb" aria-label="Путь к странице">'+link('/','Главная')+'<span aria-hidden="true">/</span><span aria-current="page">'+LABELS.get(path, 'Страница не найдена')+'</span></nav>'
    icon='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect width="40" height="40" rx="9" fill="%23355c70"/><path d="M11 29V11h18v18h-6V17h-6v12z" fill="white"/></svg>'
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{E(p['title'])}</title><meta name="description" content="{E(p['description'])}"><meta name="robots" content="{robots}"><link rel="canonical" href="{C['origin']}{path}"><meta name="theme-color" content="#355c70"><meta property="og:title" content="{E(p['title'])}"><meta property="og:description" content="{E(p['description'])}"><meta property="og:type" content="website"><meta property="og:locale" content="ru_RU"><meta property="og:url" content="{C['origin']}{path}"><meta property="og:site_name" content="{E(C['brand'])}"><meta property="og:image" content="{C['origin']}/assets/parcels.webp"><meta property="og:image:alt" content="Иллюстрация упаковки товаров {E(C['brand'])}"><meta name="twitter:card" content="summary_large_image"><link rel="preload" href="/assets/oswald.ttf" as="font" type="font/ttf" crossorigin><link rel="icon" href='data:image/svg+xml,{icon}'><link rel="stylesheet" href="/assets/style.css"><link rel="stylesheet" href="/assets/story.css"><link rel="stylesheet" href="/assets/contact.css"><link rel="stylesheet" href="/assets/warehouse-design.css"><script src="/assets/design-preview.js" defer></script><script type="application/ld+json">{json.dumps(structured,ensure_ascii=False)}</script><script id="site-data" type="application/json">{cfg}</script><script src="/assets/app.js" defer></script></head><body class="{'home-page' if path=='/' else 'service-page'}"><a href="#main" class="skip">К содержанию</a>{demo}<header class="site-header"><a class="brand" href="/" aria-label="{E(C['brand'])}: главная"><span class="brand-mark" aria-hidden="true">П</span><span>{E(C['brand'])}<small>{E(C['descriptor'])}</small></span></a><button class="menu-toggle" aria-label="Открыть меню" aria-expanded="false" aria-controls="main-nav">Меню <span aria-hidden="true">☰</span></button><nav id="main-nav" aria-label="Основная навигация">{nav}</nav>{button('Позвонить',call_href(C['contact']['phone']))}</header><main id="main" class="container">{crumb}{p['body']}</main><footer class="footer"><div class="container"><div class="footer-top"><a class="brand" href="/"><span class="brand-mark" aria-hidden="true">П</span><span>{E(C['brand'])}<small>{E(C['descriptor'])}</small></span></a><p>Хранение товара<br>и сборка заказов.</p></div><div class="footer-contact">{footer_contact}</div><div class="footer-links">{footerlinks}</div><div class="footer-bottom"><span>© {date.today().year} {E(C['brand'])}</span><span>{'Тарифы демонстрационные. Для связи используйте телефон или почту.' if C['demo'] else E(C['city'])}</span></div></div></footer></body></html>'''

if not C['demo']:
    required=['phone','address','hours']
    missing=[k for k in required if not C['contact'].get(k)]
    if missing or C['form']['mode']=='demo':
        raise SystemExit('Launch requires verified contact fields and a working form: '+', '.join(missing))
    raise SystemExit('Live form is not implemented in this demonstration. Connect and test the lead receiver before removing this launch guard.')
enhance(PAGES,C)
for path,p in PAGES.items():
    seo_h1={
      '/tarify/':'Тарифы на фулфилмент.<br>Посчитайте поставку.',
      '/fbs/':'FBS-фулфилмент.<br>Хранение и сборка заказов.',
      '/podgotovka-postavok/':'Подготовка поставок<br>на маркетплейсы.',
      '/upakovka-markirovka/':'Упаковка и маркировка<br>товаров в Ростове-на-Дону.',
      '/dostavka/':'Доставка на маркетплейсы<br>из Ростова-<wbr><span class="city-tail">на-Дону.</span>',
      '/sklad/':'Склад фулфилмента.<br>Учет и хранение товара.',
      '/kontakty/':'Контакты фулфилмента<br>в Ростове-на-Дону.'
    }
    if path in seo_h1:
        import re
        p['body']=re.sub(r'<h1>.*?</h1>', '<h1>'+seo_h1[path]+'</h1>',p['body'],count=1)
    p['body']=p['body'].replace('Уточните возможность приема вашей партии по телефону или почте.', minimum_text).replace('До первой отгрузки уточните, до какого часа передавать заказы, когда они уезжают и как склад работает в выходные.',cutoff_text)
    if path=='/podgotovka-postavok/': p['body']=p['body'].replace('по согласованному заданию.', 'по согласованному заданию. '+processing_text)
    folder=OUT/path.strip('/')
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'index.html').write_text(render(path,p),encoding='utf-8')
assets=OUT/'assets'; assets.mkdir(exist_ok=True)
for item in (ROOT/'assets').glob('*'):
    if item.is_file(): shutil.copy2(item,assets/item.name)
(assets/'zadanie-na-raschet.txt').write_text(inquiry_template(C),encoding='utf-8-sig')
(OUT/'robots.txt').write_text('User-agent: *\n'+('Disallow: /\n' if C['demo'] else 'Allow: /\n')+f'Sitemap: {C["origin"]}/sitemap.xml\n',encoding='utf-8')
(OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{E(C["origin"]+path)}</loc></url>' for path in PAGES)+'</urlset>',encoding='utf-8')
err={'title':f'Страница не найдена | {C["brand"]}','description':'Проверьте адрес или вернитесь на главную.','body':hero('Ошибка 404','Такой страницы нет.','Вернитесь на главную или выберите нужную услугу.',cta_text='На главную',cta_href='/')}
(OUT/'404.html').write_text(render('/404/',err),encoding='utf-8')
(OUT/'_headers').write_text('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n'+('  X-Robots-Tag: noindex, nofollow, noarchive\n' if C['demo'] else ''),encoding='utf-8')
print(json.dumps({'pages':len(PAGES),'output':str(OUT),'demo':C['demo']},ensure_ascii=False))
