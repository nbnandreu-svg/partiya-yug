"""Dependency-free static HTML generator. Global business data live in config/site.json."""
import argparse, json, html, shutil
from pathlib import Path
from datetime import date

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
minimum_text = f"Минимальная партия: {C['conditions']['minimumBatch']} шт." if C['conditions']['minimumBatch'] else 'Минимальный объем обслуживания пока не утвержден.'
cutoff_text = f"Задания принимаются до {C['conditions']['cutoff']}." if C['conditions']['cutoff'] else 'Время приема заданий, выходные и крайнее время передачи на каждом направлении определяются до первой отгрузки.'
processing_text = f"Срок обработки: {C['conditions']['processingTime']}." if C['conditions']['processingTime'] else 'Срок обработки согласуется по объему и заданию.'
def rub(n): return f'{n:,.2f}'.rstrip('0').rstrip('.').replace(',', ' ').replace('.', ',') + ' ₽'
def link(href, text, cls=''): return f'<a class="{cls}" href="{href}">{text}</a>'
def button(text='Обсудить поставку', href='/kontakty/#request', secondary=False): return link(href,text, 'button secondary' if secondary else 'button')
def label(text): return f'<p class="eyebrow">{text}</p>'
def section(title, body, intro='', cls=''):
    return f'<section class="section {cls}"><div class="section-head"><h2>{title}</h2>{f"<p>{intro}</p>" if intro else ""}</div>{body}</section>'
def cards(items):
    return '<div class="cards">'+''.join(f'<article class="card"><span class="index">{i+1:02}</span><h3>{h}</h3><p>{p}</p>{link(u,"Подробнее <span aria-hidden=\"true\">↗</span>","text-link") if u else ""}</article>' for i,(h,p,u) in enumerate(items))+'</div>'
def steps(items):
    return '<ol class="steps">'+''.join(f'<li><span>{i+1:02}</span><div><h3>{h}</h3><p>{p}</p></div></li>' for i,(h,p) in enumerate(items))+'</ol>'
def faq(items): return '<div class="faq">'+''.join(f'<details><summary>{q}</summary><p>{a}</p></details>' for q,a in items)+'</div>'
def photo(filename, alt, caption):
    return f'<figure class="story-image"><img src="/assets/{filename}.webp" alt="{E(alt)}" width="1536" height="1024" loading="lazy" decoding="async"><figcaption>Иллюстрация. {E(caption)}</figcaption></figure>'
def notice(text=None): return f'<p class="notice">{E(text or C["rateNote"])}</p>' if C['demo'] else ''
def hero(kicker,title,intro,aside=''):
    return f'<section class="page-hero"><div>{label(kicker)}<h1>{title}</h1><p class="lead">{intro}</p><div class="actions">{button()}</div></div>{aside}</section>'
def lead_form():
    return '''<section class="lead-section" id="request"><div><p class="eyebrow">Начнем с вашей задачи</p><h2>Одна партия.<br>Понятная задача.</h2><p>Укажите товар и объем. Этих данных достаточно, чтобы начать обсуждение состава работ.</p><span class="form-note">Демо: данные не отправляются. Не вводите личные контакты.</span></div><form class="lead-form" novalidate><label>Что нужно сделать<select name="service"><option>Подготовить партию на склад маркетплейса</option><option>Хранить товар и собирать FBS-заказы</option><option>Упаковать или промаркировать товар</option></select></label><div class="form-row"><label>Товар<input name="product" placeholder="Например, футболки" maxlength="120" required></label><label>Объем, шт.<input name="quantity" type="number" min="1" max="1000000" step="1" placeholder="500" required></label></div><button class="button" type="submit" disabled>Посмотреть пример заявки <span aria-hidden="true">↗</span></button><p class="form-result" role="status" aria-live="polite"></p><noscript><p>Для демонстрации формы включите JavaScript. Тарифы и состав услуг доступны без него.</p></noscript></form></section>'''

NAV=[('/', 'Главная'),('/tarify/','Тарифы'),('/fbs/','FBS'),('/podgotovka-postavok/','Поставки на WB и Ozon'),('/sklad/','Склад'),('/kontakty/','Контакты')]
PAGES={}
def add(path,title,description,h1,body): PAGES[path]={'title':title,'description':description,'h1':h1,'body':body}

# A functional parcel workflow occupies the hero until the illustrative asset is ready.
hero_visual='''<div class="hero-art"><img src="/assets/parcels.webp" alt="Иллюстрация упаковки: коробки и пакет для отправки" width="1200" height="800" fetchpriority="high"><div class="route-note"><span class="route-label">Товар движется. Вы видите этапы.</span><div><span>Приемка</span><b aria-hidden="true">→</b><span>Подготовка</span><b aria-hidden="true">→</b><span>Отгрузка</span></div></div><span class="image-caption">Иллюстрация</span></div>'''
home=f'''<section class="home-hero"><div class="hero-copy">{label('Ozon / Wildberries · Ростов-на-Дону')}<h1>Фулфилмент<br>в Ростове-<br>на-Дону<span class="dot">.</span></h1><p class="lead">Принимаем, храним и готовим товары к продаже. От целой партии на склад маркетплейса до каждого FBS-заказа.</p><div class="actions">{button()}{link('#services','Выбрать услугу','text-link')}</div></div>{hero_visual}</section>
<div class="service-strip"><span>Приемка и хранение</span><span>Упаковка и маркировка</span><span>Сборка FBS</span><span>Поставки на маркетплейсы</span></div>
<section class="section" id="services"><div class="section-head"><h2>Два способа<br>передать нам логистику</h2><p>Выберите по тому, где хранится товар и кто получает заказ от покупателя.</p></div><div class="model-grid"><article class="model-card"><div class="model-top"><span class="pill">Партиями</span><span class="model-code">FBO / FBW</span></div><h3>Подготовить поставку<br>на склад маркетплейса</h3><p>Пересчитать товар, проверить, упаковать, нанести этикетки и собрать короба для отгрузки.</p>{link('/podgotovka-postavok/','Как готовим партию <span aria-hidden="true">↗</span>','model-link')}</article><article class="model-card blue"><div class="model-top"><span class="pill">По заказам</span><span class="model-code">FBS</span></div><h3>Хранить у нас.<br>Отправлять по мере продаж.</h3><p>Товар остается на складе фулфилмента. После продажи собираем заказ и передаем его площадке.</p>{link('/fbs/','Как работает FBS <span aria-hidden="true">↗</span>','model-link')}</article></div></section>'''
home+=section('Порядок на каждом этапе',steps([('Согласовать задание','Указать артикулы, количество, требования к проверке и упаковке.'),('Зафиксировать приемку','Сверить фактическое количество с документами и отдельно отметить расхождения.'),('Подготовить и передать товар','Собрать партию или заказ по согласованному заданию и передать на нужное направление.'),('Сверить результат','Получить сведения о выполненных операциях и остатке товара.')]),'От первой коробки до отгрузки. Детали процесса фиксируются до начала работ.')
home+=photo('packing','Проверка упаковки и нанесение этикетки на короб','Проверка упаковки перед отправкой')
home+=section('Передать товар<br>с понятными условиями', '<div class="trust-grid"><div class="trust-big"><span class="index">До первой поставки</span><h3>Проверьте склад.<br>Разберите договор.</h3><p>Адрес, учет товара, доступ к информации и порядок действий при расхождениях должны быть понятны до передачи партии.</p>'+link('/sklad/','Что уточнить перед стартом ↗','text-link')+'</div><div class="trust-list"><article><h3>Что принято</h3><p>Артикулы, количество и замечания при приемке.</p></article><article><h3>Что выполнено</h3><p>Состав работ, упаковка и переданные отправления.</p></article><article><h3>Что осталось</h3><p>Остатки, возвраты и расхождения, требующие решения.</p></article></div></div>')
home+=section('Частые вопросы',faq([('Можно передать только упаковку партии?','Да. В задании можно выделить отдельные операции: приемку, упаковку, маркировку или подготовку поставки. Состав работ и ограничения согласовываются до приема товара.'),('Чем FBS отличается от подготовки поставки?','При FBS товар хранится на складе фулфилмента, а отправления собираются после заказов покупателей. При подготовке FBO/FBW собирается партия для последующего хранения и обработки на складе маркетплейса.'),('Что нужно, чтобы обсудить поставку?','Категория и размеры товара, количество единиц и артикулов, схема работы, требования к упаковке и направление доставки. Для FBS также нужен ожидаемый объем заказов и запас на хранении.'),('Есть ли минимальная партия?','Минимальный объем обслуживания пока не утвержден. Его согласуют до передачи товара.')] ))
home+=lead_form()
add('/',f'Фулфилмент в Ростове-на-Дону для Ozon и Wildberries | {C["brand"]}','Подготовка поставок на Ozon и Wildberries, хранение, упаковка и сборка FBS. Состав услуг и условия работы в Ростове-на-Дону.','Фулфилмент в Ростове-на-Дону',home)

tariffs=hero('Тарифы','Стоимость согласуем<br>под вашу задачу.','Цена зависит от товара, упаковки, объема и схемы отгрузки. Напишите, что нужно сделать, и мы разберем состав работ.')+lead_form()
add('/tarify/',f'Тарифы на фулфилмент в Ростове-на-Дону | {C["brand"]}','Стоимость фулфилмента согласуется под товар, упаковку, хранение и схему отгрузки.','Стоимость согласуем под вашу задачу.',tariffs)

fbs=hero('Хранение и сборка заказов','Ваш запас на складе.<br>Каждый заказ в работе.','Фулфилмент FBS для Ozon и Wildberries в Ростове-на-Дону: приемка запаса, хранение, подбор товара, упаковка и передача заказов площадке.')
fbs+=section('Как проходит заказ',steps([('Принять и разместить запас','Сверить артикулы и количество. Согласовать, как передаются задания и обновляются остатки.'),('Получить задание на сборку','Проверить состав заказа, требования площадки и согласованный срок передачи.'),('Подобрать и упаковать','Собрать нужный товар, нанести этикетку заказа, подготовить к передаче.'),('Передать и сверить','Зафиксировать отправление. Возвраты учитывать отдельно от доступного к продаже остатка.')]))
fbs+=photo('fbs','Аккуратно размещенные товары и пакеты на стеллаже','Организованное хранение запаса для FBS')
fbs+=section('Согласовать до запуска FBS',cards([('График работы','Время приема заданий, выходные и крайнее время передачи на каждом направлении определяются до первой отгрузки.',None),('Учет остатков','Согласуйте формат отчета и частоту обновления. Возможность интеграции с кабинетом продавца уточняется отдельно.',None),('Возвраты','При приемке возврата важно зафиксировать состояние и получить решение: вернуть в запас, переупаковать или вывести.',None)]))
fbs+=section('Когда подходит FBS','<div class="editorial"><p>Товар остается у оператора, а покупатель оформляет заказ на маркетплейсе. Такая схема позволяет работать с запасом вне склада площадки, но требует регулярной сборки и соблюдения ее сроков.</p><p>При выборе сравните полную стоимость хранения, обработки и передачи заказа. Условия маркетплейса и скорость доставки зависят от направления и модели работы.</p></div>')
fbs+=lead_form()
add('/fbs/',f'FBS фулфилмент для Ozon и Wildberries в Ростове | {C["brand"]}','Хранение товара, сборка FBS-заказов, упаковка и передача на Ozon и Wildberries. Состав работ и учет остатков.','Ваш запас на складе. Каждый заказ в работе.',fbs)

prep=hero('Подготовка поставок FBO / FBW','Партия готова<br>к передаче на маркетплейс.','От приемки товара до коробов с нужными этикетками. Готовим поставки для Ozon и Wildberries по согласованному заданию.')
prep+=section('Что происходит с партией',steps([('Сверяем товар','Сопоставляем количество и артикулы с документами. Видимые повреждения и расхождения выделяем отдельно.'),('Выполняем задание','Проверяем, комплектуем, упаковываем и наносим согласованные этикетки.'),('Собираем поставку','Распределяем товар по коробам или паллетам, сверяем состав и маркировку грузовых мест.'),('Передаем на направление','Согласовываем склад назначения, слот и документы. Факт передачи фиксируется по доступным документам.')]))
prep+=photo('shipment','Группа коробов на паллете, готовая к отправке','Собранная партия перед передачей на маркетплейс')
prep+=section('Для расчета подготовьте',cards([('Данные о товаре','Категория, количество, число артикулов, габариты и вес единицы.',None),('Задание на подготовку','Вид упаковки, глубина проверки, этикетки и необходимость формирования наборов.',None),('Данные о поставке','Площадка и склад назначения, плановая дата, число коробов или паллет.',None)]))
prep+=section('Ozon и Wildberries','<div class="model-grid"><article class="card"><span class="pill">Ozon · FBO</span><h3>Подготовка по заданию поставки</h3><p>Состав партии, этикетки и документы сверяются с актуальными требованиями выбранного склада Ozon.</p></article><article class="card"><span class="pill">Wildberries · FBW</span><h3>Подготовка к отгрузке на WB</h3><p>Товарная и транспортная упаковка, маркировка коробов и паллет проверяются для конкретной поставки.</p></article></div>','Правила площадок могут меняться. Окончательные требования сверяются перед выполнением задания.')+lead_form()
add('/podgotovka-postavok/',f'Подготовка поставок на Ozon и Wildberries в Ростове | {C["brand"]}','Приемка, пересчет, проверка, упаковка и маркировка партий для поставок FBO и FBW. Подготовка коробов и паллет в Ростове-на-Дону.','Партия готова к передаче на маркетплейс.',prep)

pack=hero('Упаковка и маркировка','Упаковка под товар.<br>Этикетка по заданию.','Подготовка товаров для маркетплейсов в Ростове-на-Дону. Отдельная операция или часть полного цикла обработки партии.')
pack+=section('Выберите состав работ',cards([('Индивидуальная упаковка','Пакет, коробка или дополнительная защита. Материал и размеры выбираются под товар и требования площадки.',None),('Этикетирование','Печать и нанесение согласованных этикеток. Нужны корректные исходные данные и образец размещения.',None),('Комплектация и вложения','Сборка наборов, вложение инструкций и других материалов по заданию. Состав комплекта фиксируется заранее.',None),('Переупаковка','Замена поврежденной или неподходящей упаковки. Состояние товара проверяется до выполнения операции.',None)]))
pack+=photo('packing','Проверка коробки перед упаковкой и маркировкой','Пример работы с упаковкой и этикеткой')
pack+=section('Образец до всей партии','<div class="editorial"><p>Для нестандартной упаковки сначала согласуйте образец: материал, положение этикетки, вложения и порядок фиксации. Он поможет одинаково обработать всю партию.</p><p>Нанесение готового кода маркировки и операции в системе Честный знак являются разными задачами. Их состав и доступность нужно согласовать отдельно.</p></div>')
pack+=section('Проверка товара',faq([('Что означает проверка на видимый брак?','Осмотр доступных поверхностей по согласованным признакам. Он не заменяет проверку работоспособности, лабораторную проверку или экспертизу.'),('Можно заказать подробную проверку?','Сначала нужно описать критерии: размеры, швы, комплектацию или работу устройства. Возможность и цену такой проверки определяют по заданию.'),('Материалы входят в работу?','Материал подбирается под товар. Его тип, размер и стоимость согласуются отдельно от упаковочной операции.')]))+lead_form()
add('/upakovka-markirovka/',f'Упаковка и маркировка товаров в Ростове-на-Дону | {C["brand"]}','Упаковка, этикетирование, комплектация наборов и переупаковка товаров для Ozon и Wildberries. Состав работ и материалов.','Упаковка под товар. Этикетка по заданию.',pack)

delivery=hero('Доставка на маркетплейсы','Отгрузка начинается<br>с правильной подготовки.','Передача партий и FBS-заказов на Ozon и Wildberries из Ростова-на-Дону. Маршрут и стоимость зависят от склада назначения и параметров груза.')
delivery+=section('Два вида отправлений',cards([('Короба и паллеты','Подготовленные партии для склада маркетплейса. Для расчета нужны размеры, вес, число мест и направление.','/podgotovka-postavok/'),('Заказы FBS','Отдельные отправления, собранные по заказам покупателей. Порядок передачи и время отсечения согласуются по направлению.','/fbs/')]))
delivery+=section('Что проверить перед выездом',steps([('Направление и дата','Адрес склада или пункта приема, способ поставки и доступность приема.'),('Параметры груза','Количество коробов или паллет, размеры, вес и ограничения перевозки.'),('Этикетки и документы','Соответствие грузовых мест поставке, маркировка и необходимые документы.'),('Порядок подтверждения','Какие документы или статусы будут доступны после передачи и что делать при отказе в приемке.')]))
delivery+=photo('shipment','Подготовленные к перевозке короба на паллете','Партия после упаковки и комплектации')
delivery+=section('Направления и график','<div class="callout"><h3>Согласуются для вашей поставки</h3><p>В макете нет утвержденного расписания и списка складов назначения. Перед отгрузкой нужно проверить доступный маршрут, дату и условия приемки.</p>'+button()+'</div>')+lead_form()
add('/dostavka/',f'Доставка на склады Ozon и Wildberries из Ростова | {C["brand"]}','Доставка коробов, паллет и FBS-отправлений на маркетплейсы. Параметры груза, подготовка документов и согласование направления.','Отгрузка начинается с правильной подготовки.',delivery)

warehouse=hero('Склад и условия работы','Понятно, где товар.<br>Понятно, что с ним.','Перед первой поставкой разберите порядок приемки, учета, хранения и действий при расхождениях. Эти условия фиксируются в документах.')
warehouse+=section('Что проверить до передачи товара',cards([('Сам склад','Фактический адрес, условия размещения вашего товара, доступ на разгрузку и возможность посещения.',None),('Приемку и учет','Как сверяются артикулы и количество, фиксируется состояние партии и ведутся остатки.',None),('Доступ к информации','В каком формате предоставляются сведения об операциях, остатках и возвратах.',None),('Ответственность сторон','Как рассматривается претензия, чем подтверждается стоимость товара и какие условия содержит договор.',None)]))
warehouse+=section('Если обнаружено расхождение',steps([('Зафиксировать факт','Указать поставку, артикул, количество и характер расхождения. Сохранить доступные документы и материалы.'),('Сверить операции','Сопоставить приемку, задания, отгрузки и возвраты. Определить, на каком этапе возник вопрос.'),('Согласовать решение','Применить условия договора. Исправление учета, повторная обработка и возмещение являются разными решениями.')]))
warehouse+=section('Сведения о складе','<div class="warehouse-placeholder"><span class="index">Данные для запуска</span><h3>Здесь будут реальные фотографии<br>и адрес склада</h3><p>Доступ к видео, страхование и условия ответственности пока не подтверждены. В макете они не заявлены как действующие преимущества.</p></div>')
warehouse+=section('Частые вопросы о сохранности',faq([('Можно ли посетить склад?','Условия и время посещения нужно согласовать. Контакты и адрес будут добавлены после подтверждения данных бизнеса.'),('Есть ли страхование товара?','Подтвержденных сведений о полисе нет. При обсуждении страхования необходимо отдельно проверить объект, риски, исключения и размер покрытия.'),('FBS гарантирует сохранность запаса?','Схема FBS определяет, где хранится товар и как собираются заказы. Сама по себе она не гарантирует защиту от происшествий. Значение имеют фактические условия хранения и договор.')]))+lead_form()
add('/sklad/',f'Склад фулфилмента и условия хранения в Ростове | {C["brand"]}','Приемка, учет остатков и порядок разбора расхождений. Что проверить перед передачей товара на склад фулфилмента.','Понятно, где товар. Понятно, что с ним.',warehouse)

contact_items=[('Город',C['city']),('Адрес склада',C['contact']['address'] or 'Будет добавлен после подтверждения'),('Телефон',C['contact']['phone'] or 'Пока не указан'),('Электронная почта',C['contact']['email'] or 'Пока не указана'),('Время работы',C['contact']['hours'] or 'Уточняется перед запуском')]
contacts=hero('Контакты','Обсудим вашу<br>первую поставку.','Начать можно с описания товара, объема и задачи. Адрес, реквизиты и рабочие контакты появятся после подтверждения.')
contacts+=section('Как связаться','<dl class="contact-list">'+''.join(f'<div><dt>{n}</dt><dd>{E(str(v))}</dd></div>' for n,v in contact_items)+'</dl>')+lead_form()
add('/kontakty/',f'Контакты фулфилмента в Ростове-на-Дону | {C["brand"]}','Обсуждение подготовки партии или FBS в Ростове-на-Дону.','Обсудим вашу первую поставку.',contacts)

def render(path,p):
    nav=''.join(link(u,n,'active' if path==u else '') for u,n in NAV)
    footerlinks=''.join(link(u,n) for u,n in NAV+[("/upakovka-markirovka/","Упаковка и маркировка"),("/dostavka/","Доставка")])
    public={k:v for k,v in C.items() if k not in ('rates','defaults')}
    cfg=json.dumps(public,ensure_ascii=False).replace('</','<\\/')
    robots='noindex, nofollow, noarchive' if C['demo'] else 'index, follow'
    structured={'@context':'https://schema.org','@type':'WebSite','name':C['brand'],'url':C['origin']+'/','inLanguage':'ru-RU'}
    demo='<div class="demo-bar"><span>Демонстрационный сайт</span><span>Тарифы и условия будут уточнены перед запуском</span></div>' if C['demo'] else ''
    crumb='' if path=='/' else '<div class="breadcrumb">'+link('/','Главная')+'<span>/</span><span>'+next((n for u,n in NAV if u==path), 'Услуги')+'</span></div>'
    icon='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect width="40" height="40" rx="9" fill="%231d48ee"/><path d="M11 29V11h18v18h-6V17h-6v12z" fill="white"/></svg>'
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{E(p['title'])}</title><meta name="description" content="{E(p['description'])}"><meta name="robots" content="{robots}"><link rel="canonical" href="{C['origin']}{path}"><meta name="theme-color" content="#1d48ee"><meta property="og:title" content="{E(p['title'])}"><meta property="og:description" content="{E(p['description'])}"><meta property="og:type" content="website"><meta property="og:locale" content="ru_RU"><meta property="og:url" content="{C['origin']}{path}"><meta property="og:site_name" content="{E(C['brand'])}"><link rel="icon" href='data:image/svg+xml,{icon}'><link rel="stylesheet" href="/assets/style.css"><link rel="stylesheet" href="/assets/story.css"><script type="application/ld+json">{json.dumps(structured,ensure_ascii=False)}</script><script id="site-data" type="application/json">{cfg}</script><script src="/assets/app.js" defer></script></head><body><a href="#main" class="skip">К содержанию</a>{demo}<header class="site-header"><a class="brand" href="/" aria-label="{E(C['brand'])} — главная"><span class="brand-mark" aria-hidden="true">П</span><span>{E(C['brand'])}<small>{E(C['descriptor'])}</small></span></a><button class="menu-toggle" aria-label="Открыть меню" aria-expanded="false" aria-controls="main-nav">Меню <span aria-hidden="true">☰</span></button><nav id="main-nav" aria-label="Основная навигация">{nav}</nav>{button('Обсудить ↗')}</header><main id="main" class="container">{crumb}{p['body']}</main><footer class="footer"><div class="container"><div class="footer-top"><a class="brand" href="/"><span class="brand-mark" aria-hidden="true">П</span><span>{E(C['brand'])}<small>{E(C['descriptor'])}</small></span></a><p>От первой партии<br>до следующего заказа.</p></div><div class="footer-links">{footerlinks}</div><div class="footer-bottom"><span>© {date.today().year} {E(C['brand'])}</span><span>{'Макет. Заявки не отправляются. Данные не сохраняются.' if C['demo'] else E(C['city'])}</span></div></div></footer></body></html>'''

if not C['demo']:
    required=['phone','address','hours']
    missing=[k for k in required if not C['contact'].get(k)]
    if missing or C['form']['mode']=='demo':
        raise SystemExit('Launch requires verified contact fields and a working form: '+', '.join(missing))
    raise SystemExit('Live form is not implemented in this demonstration. Connect and test the lead receiver before removing this launch guard.')
for path,p in PAGES.items():
    seo_h1={
      '/tarify/':'Тарифы на фулфилмент.<br>Стоимость под задачу.',
      '/fbs/':'FBS-фулфилмент.<br>Хранение и сборка заказов.',
      '/podgotovka-postavok/':'Подготовка поставок<br>на Ozon и Wildberries.',
      '/upakovka-markirovka/':'Упаковка и маркировка<br>товаров для маркетплейсов.',
      '/dostavka/':'Доставка на Ozon<br>и Wildberries из Ростова.',
      '/sklad/':'Склад фулфилмента.<br>Учет и хранение товара.',
      '/kontakty/':f'Контакты<br>{E(C["brand"])}.'
    }
    if path in seo_h1:
        import re
        p['body']=re.sub(r'<h1>.*?</h1>', '<h1>'+seo_h1[path]+'</h1>',p['body'],count=1)
    p['body']=p['body'].replace('Минимальный объем обслуживания пока не утвержден.', minimum_text).replace('Время приема заданий, выходные и крайнее время передачи на каждом направлении определяются до первой отгрузки.',cutoff_text)
    if path=='/podgotovka-postavok/': p['body']=p['body'].replace('по согласованному заданию.', 'по согласованному заданию. '+processing_text)
    folder=OUT/path.strip('/')
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'index.html').write_text(render(path,p),encoding='utf-8')
assets=OUT/'assets'; assets.mkdir(exist_ok=True)
for item in (ROOT/'assets').glob('*'):
    if item.is_file(): shutil.copy2(item,assets/item.name)
(OUT/'robots.txt').write_text('User-agent: *\n'+('Disallow: /\n' if C['demo'] else 'Allow: /\n')+f'Sitemap: {C["origin"]}/sitemap.xml\n',encoding='utf-8')
(OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{E(C["origin"]+path)}</loc></url>' for path in PAGES)+'</urlset>',encoding='utf-8')
err={'title':f'Страница не найдена | {C["brand"]}','description':'Проверьте адрес или вернитесь на главную.','body':hero('Ошибка 404','Такой страницы нет.','Вернитесь на главную или выберите нужную услугу.')}
(OUT/'404.html').write_text(render('/404/',err),encoding='utf-8')
(OUT/'_headers').write_text('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n'+('  X-Robots-Tag: noindex, nofollow, noarchive\n' if C['demo'] else ''),encoding='utf-8')
print(json.dumps({'pages':len(PAGES),'output':str(OUT),'demo':C['demo']},ensure_ascii=False))
