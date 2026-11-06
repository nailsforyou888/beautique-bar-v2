"""Tell Bing (and so ChatGPT search and Copilot) which pages changed in this publish, via IndexNow.

Runs in the Publish website workflow after the upload, on main only. It reads the production sitemap that
make_production.py just wrote and submits the pages whose lastmod is today (their main content changed), plus
llms.txt. The key file lives at opus-design-v1/<KEY>.txt, so it ships with the site. It never fails the publish.
"""
import datetime
import json
import re
import sys
import urllib.request
from pathlib import Path

KEY = 'cf09dcaaaa76bf6fd4eeb694e8d88450'
SRC = Path(__file__).resolve().parent
SITEMAP = SRC.parent / 'opus-site-production' / 'sitemap.xml'


def main():
    sys.path.insert(0, str(SRC))
    from site_config import SITE_URL
    xml = SITEMAP.read_text()
    today = datetime.date.today().isoformat()
    urls = [loc for loc, mod in re.findall(r'<loc>(.*?)</loc><lastmod>(.*?)</lastmod>', xml) if mod == today]
    if not urls:
        print('IndexNow: no page content changed today; nothing to send.')
        return
    urls.append(f'{SITE_URL}/llms.txt')
    body = {'host': SITE_URL.split('://', 1)[1], 'key': KEY, 'keyLocation': f'{SITE_URL}/{KEY}.txt', 'urlList': urls}
    req = urllib.request.Request('https://api.indexnow.org/IndexNow', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json; charset=utf-8'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f'IndexNow: sent {len(urls)} URL(s), HTTP {resp.status}.')
    except Exception as exc:  # never fail the publish over a search-engine ping
        print(f'::warning title=IndexNow::not sent ({exc}); the weekly Growth HQ run will catch up.')


if __name__ == '__main__':
    main()
