"""Page metadata and factual structured data, shared by local and Pages builds."""
from html import escape
from urllib.parse import quote

LABELS = {
    '/': 'Главная', '/tarify/': 'Тарифы', '/fbs/': 'FBS-фулфилмент',
    '/podgotovka-postavok/': 'Подготовка поставок',
    '/upakovka-markirovka/': 'Упаковка и маркировка',
    '/dostavka/': 'Доставка на маркетплейсы', '/sklad/': 'Склад и хранение',
    '/kontakty/': 'Контакты', '/404/': 'Страница не найдена'
}
RELATED = {
    '/': [('/upakovka-markirovka/', 'Нужны только упаковка или этикетки'), ('/dostavka/', 'Партия готова, нужна доставка'), ('/sklad/', 'Нужно обсудить хранение товара')],
    '/tarify/': [('/podgotovka-postavok/', 'Что входит в подготовку партии'), ('/fbs/', 'Как проходит сборка FBS-заказов')],
    '/fbs/': [('/sklad/', 'Условия хранения и учет остатков'), ('/dostavka/', 'Передача заказов на маркетплейсы')],
    '/podgotovka-postavok/': [('/upakovka-markirovka/', 'Упаковка, этикетки и комплектация'), ('/dostavka/', 'Доставка готовой партии')],
    '/upakovka-markirovka/': [('/podgotovka-postavok/', 'Подготовка всей поставки'), ('/tarify/', 'Пример расчета стоимости')],
    '/dostavka/': [('/podgotovka-postavok/', 'Если товар еще нужно подготовить'), ('/kontakty/', 'Адрес склада и согласование приезда')],
    '/sklad/': [('/fbs/', 'Хранение со сборкой FBS-заказов'), ('/kontakty/', 'Контакты и адрес на карте')]
}

def structured_data(config, path, page):
    origin = config['origin'].rstrip('/')
    company_id = origin + '/#business'
    graph = [
        {'@type': 'WebSite', '@id': origin + '/#website', 'name': config['brand'],
         'url': origin + '/', 'inLanguage': 'ru-RU', 'publisher': {'@id': company_id}},
        {'@type': 'WebPage', '@id': origin + path + '#page', 'url': origin + path,
         'name': page['title'], 'description': page['description'], 'inLanguage': 'ru-RU',
         'isPartOf': {'@id': origin + '/#website'}}
    ]
    # Only supplied facts. No stock images, ratings, hours, priceRange or fake coordinates.
    contact = config['contact']
    if contact.get('address') and contact.get('phone'):
        digits = ''.join(x for x in contact['phone'] if x.isdigit())
        phone = '+7' + digits[1:] if digits.startswith('8') else '+' + digits
        graph.append({'@type': 'LocalBusiness', '@id': company_id, 'name': config['brand'],
                      'url': origin + '/', 'telephone': phone, 'email': contact['email'],
                      'address': {'@type': 'PostalAddress', 'addressCountry': 'RU',
                                  'addressLocality': config['city'],
                                  'streetAddress': contact['address'].removeprefix(config['city'] + ', ')}})
    if (path != '/' and path in RELATED) or path == '/kontakty/':
        crumb_id = origin + path + '#breadcrumb'
        graph[1]['breadcrumb'] = {'@id': crumb_id}
        graph.append({'@type': 'BreadcrumbList', '@id': crumb_id, 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': LABELS['/'], 'item': origin + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': LABELS[path], 'item': origin + path}
        ]})
    return {'@context': 'https://schema.org', '@graph': graph}

def enhance(pages, config):
    descriptions = {
        '/': 'Фулфилмент в Ростове-на-Дону для Ozon и Wildberries. Подготовка партий, упаковка, хранение и сборка FBS. Обсудите свой товар и объем работ.',
        '/tarify/': 'Калькулятор фулфилмента в Ростове-на-Дону: подготовка партии и FBS. Демонстрационные цены. Уточните стоимость работ и материалов для своего товара.',
        '/fbs/': 'FBS-фулфилмент в Ростове-на-Дону для Ozon и Wildberries. Хранение, подбор, упаковка и передача заказов. Обсудите график и расчет под свой объем.',
        '/podgotovka-postavok/': 'Подготовка поставок Ozon FBO и Wildberries FBW в Ростове-на-Дону. Пересчет, проверка, упаковка и маркировка. Уточните состав работ и доставку.',
        '/upakovka-markirovka/': 'Упаковка и маркировка товаров для Ozon и Wildberries в Ростове-на-Дону. Этикетки, наборы и переупаковка. Пришлите фото и требования для расчета.',
        '/sklad/': 'Хранение товаров на складе фулфилмента в Ростове-на-Дону. Приемка, учет и сверка остатков. Уточните условия для вашего товара и согласуйте визит.'
    }
    for path, description in descriptions.items():
        pages[path]['description'] = description
    for path, links in RELATED.items():
        heading = 'Если нужна отдельная работа' if path == '/' else 'По вашей задаче'
        block = '<section class="related-services"><h2>' + heading + '</h2><ul>'
        block += ''.join('<li><a href="' + url + '">' + escape(title) + '</a></li>' for url, title in links)
        block += '</ul></section>'
        pages[path]['body'] = pages[path]['body'].replace('<section class="lead-section"', block + '<section class="lead-section"', 1)
    download = '<a class="brief-download" href="/assets/zadanie-na-raschet.txt" download>Скачать список данных для расчета</a>'
    for path in ('/', '/tarify/', '/fbs/', '/podgotovka-postavok/'):
        pages[path]['body'] = pages[path]['body'].replace('<div class="contact-actions">', '<div class="contact-actions">' + download, 1)
    address = config['contact']['address'].split(', склад')[0]
    maps_url = 'https://yandex.ru/maps/?text=' + quote(address)
    pages['/kontakty/']['body'] += '<section class="arrival"><h2>Перед приездом на склад</h2><p>Согласуйте время, въезд и место разгрузки по телефону. Сообщите, какой груз и на какой машине привезете.</p><a class="button secondary" href="' + maps_url + '">Найти адрес на Яндекс Картах</a><p class="small">Ссылка открывает поиск по адресу здания. Место въезда и разгрузки уточните у склада.</p></section>'
    pages['/fbs/']['body'] = pages['/fbs/']['body'].replace('>Хранение и сборка заказов</p>', '>FBS в Ростове-на-Дону</p>', 1)

def inquiry_template(config):
    return f'''Данные для расчета услуг {config['brand']}

Заполните подходящие пункты и отправьте на {config['contact']['email']}.
Если какой-то параметр неизвестен, оставьте пометку. Этот файл не отправляет заявку.

Что нужно: подготовить партию / собирать FBS-заказы / упаковать / доставить / хранить.
Товар и количество артикулов:
Количество единиц:
Размеры и вес единицы:
Что уже упаковано и промаркировано:
Нужные операции и упаковочные материалы:
Ozon или Wildberries, схема работы:
Дата и склад или пункт назначения:
Число, размеры и вес коробов или паллет:

Для FBS:
Заказов в обычный день и в пик:
Товаров в одном заказе:
Запас и срок хранения:
Как сейчас передаются задания на сборку:
Нужна ли обработка возвратов:

Вопросы по товару или условиям хранения:
Как с вами связаться:

При необходимости приложите фото товара и образец этикетки.
'''
