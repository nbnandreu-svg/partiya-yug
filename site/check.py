"""Validate the generated site before and after the GitHub Pages path rewrite."""
import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags, self.ids, self.scripts, self.parts = [], set(), {}, {}
        self.capture = None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, 'Duplicate HTML id: ' + attrs['id']
            self.ids.add(attrs['id'])
        if tag in ('title', 'h1'):
            self.capture = tag
            self.parts.setdefault(tag, []).append('')
        if tag == 'script':
            self.capture = attrs.get('id') or attrs.get('type')
            if self.capture:
                self.scripts[self.capture] = ''

    def handle_endtag(self, tag):
        if tag in ('script', 'title', 'h1'):
            self.capture = None

    def handle_data(self, data):
        if self.capture in ('title', 'h1'):
            self.parts[self.capture][-1] += data
        elif self.capture in self.scripts:
            self.scripts[self.capture] += data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).parent / 'dist')
    parser.add_argument('--base', default='')
    args = parser.parse_args()
    root, base = args.root.resolve(), args.base.rstrip('/')
    pages = {p.resolve(): Page(p.read_text(encoding='utf-8')) for p in root.rglob('*.html')}
    titles, descriptions, canonicals = [], [], []

    def check_local(url, file):
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc:
            return
        path = unquote(parsed.path)
        if path.startswith('/'):
            if base:
                assert path.startswith(base + '/'), (file, 'Missing project prefix', url)
                path = path[len(base):]
            target = root / path.lstrip('/')
        elif path:
            target = file.parent / path
        else:
            target = file
        if target.is_dir():
            target /= 'index.html'
        target = target.resolve()
        assert target.is_relative_to(root) and target.exists(), (file, 'Missing resource', url)
        if parsed.fragment:
            assert parsed.fragment in pages[target].ids, (file, 'Missing anchor', url)

    for file, page in pages.items():
        assert len(page.parts.get('h1', [])) == 1, file
        assert len(page.parts.get('title', [])) == 1, file
        titles.append(page.parts['title'][0])
        meta = {a.get('name') or a.get('property'): a.get('content') for t, a in page.tags if t == 'meta'}
        assert meta.get('description') and meta.get('og:image'), file
        descriptions.append(meta['description'])
        data = json.loads(page.scripts['site-data'])
        assert not data['demo'] or 'noindex' in meta.get('robots', ''), file
        route = '/' if file == root / 'index.html' else '/' + file.parent.relative_to(root).as_posix() + '/'
        if file.name == '404.html':
            route = '/404/'
        canonical = [a['href'] for t, a in page.tags if t == 'link' and a.get('rel') == 'canonical']
        assert canonical == [data['origin'] + route], (file, canonical)
        assert 'nbnandreu.chatgpt.site' not in canonical[0], file
        if file.name != '404.html':
            canonicals.append(canonical[0])
        graph = json.loads(page.scripts['application/ld+json'])['@graph']
        business = next(x for x in graph if x['@type'] == 'LocalBusiness')
        assert business['name'] == data['brand']
        assert business['email'] == data['contact']['email']
        assert business['address']['addressLocality'] == data['city']
        assert business['address']['streetAddress'] == data['contact']['address'].removeprefix(data['city'] + ', ')
        assert not any(k in business for k in ('aggregateRating', 'review', 'priceRange', 'geo', 'image'))
        if route not in ('/', '/404/'):
            crumb = next(x for x in graph if x['@type'] == 'BreadcrumbList')['itemListElement']
            assert crumb[-1]['item'] == canonical[0]
            assert crumb[-1]['name'] != 'Услуги'
        for tag, attrs in page.tags:
            if tag in ('a', 'img', 'link', 'script'):
                url = attrs.get('href') or attrs.get('src')
                if url:
                    check_local(url, file)
            if tag == 'img':
                assert attrs.get('alt') and attrs.get('width') and attrs.get('height'), file
        if route == '/tarify/':
            assert any(a.get('id') == 'calc-lines' and 'hidden' in a for t, a in page.tags)
        if route == '/fbs/':
            assert any(t == 'img' and a.get('loading') == 'eager' and a.get('fetchpriority') == 'high' for t, a in page.tags)
    assert len(titles) == len(set(titles)), 'Duplicate title'
    assert len(descriptions) == len(set(descriptions)), 'Duplicate description'
    xml = ElementTree.parse(root / 'sitemap.xml')
    locations = [x.text for x in xml.findall('.//{*}loc')]
    assert set(locations) == set(canonicals) and len(locations) == len(canonicals)
    for file in root.rglob('*.css'):
        for url in re.findall(r'url\([\'\"]?([^\)\'\"]+)', file.read_text(encoding='utf-8')):
            check_local(url, file)
    assert data['contact']['email'] in (root / 'assets/zadanie-na-raschet.txt').read_text(encoding='utf-8-sig')
    print(f'PASS: {len(pages)} HTML pages. Metadata, links, assets, schema, sitemap, demo guard, hidden price breakdown. Base: {base or "/"}')


if __name__ == '__main__':
    main()
