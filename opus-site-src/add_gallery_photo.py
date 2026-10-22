#!/usr/bin/env python3
"""Add one nail photo to the top of the gallery (beautiquebar.com/gallery/).

    python3 opus-site-src/add_gallery_photo.py PHOTO "Caption" [--drive-id ID] [--file slug] [--crop 0.1,0,0.9,1]

- PHOTO can be JPG, PNG or HEIC/HEIF (HEIC needs: pip install pillow-heif).
- Rotation from the phone is applied, and ALL metadata (GPS location, camera, date) is stripped.
- Writes opus-design-v1/img/work-<slug>.webp (long side max 1600px) and work-<slug>-sm.webp (720px wide),
  then adds the photo as the newest entry in content/gallery.yml.
- --drive-id: the Google Drive file id it came from; the script refuses a photo that was already added.
- --crop: optional box as fractions of width/height (left,top,right,bottom) to trim clutter around the hands.
Then run build.py to check, and commit. build.py makes the -xs/-800/-1200 copies itself.
"""
import argparse, datetime, re, sys
from pathlib import Path

import yaml
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / 'opus-design-v1' / 'img'
DATA = ROOT / 'content' / 'gallery.yml'
FULL, SMALL = 1600, 720


def slugify(text):
    s = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return s[:40].rstrip('-') or 'set'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('photo')
    ap.add_argument('caption')
    ap.add_argument('--drive-id', default='')
    ap.add_argument('--file', default='', help='slug for the file name (default: from the caption)')
    ap.add_argument('--crop', default='', help='left,top,right,bottom as fractions, e.g. 0,0.1,1,0.9')
    a = ap.parse_args()

    caption = a.caption.strip()
    if not 2 <= len(caption) <= 40:
        sys.exit('Caption should be 2-40 characters, e.g. "Chocolate stiletto with hearts".')

    text = DATA.read_text()
    data = yaml.safe_load(text) or {}
    photos = data.get('photos') or []
    if a.drive_id and any(p.get('drive_id') == a.drive_id for p in photos):
        sys.exit(f'Drive file {a.drive_id} is already in the gallery.')

    slug = slugify(a.file or caption)
    taken = {p['file'] for p in photos} | {f.stem[5:] for f in IMG.glob('work-*.webp')}
    base, n = slug, 2
    while slug in taken:
        slug, n = f'{base}-{n}', n + 1

    if a.photo.lower().endswith(('.heic', '.heif')):
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            sys.exit('HEIC photo: run  pip install pillow-heif  first.')
    im = Image.open(a.photo)
    im = ImageOps.exif_transpose(im).convert('RGB')  # fixes rotation; new image carries no metadata
    if a.crop:
        l, t, r, b = (float(x) for x in a.crop.split(','))
        W, H = im.size
        im = im.crop((round(l * W), round(t * H), round(r * W), round(b * H)))
    im.thumbnail((FULL, FULL), Image.LANCZOS)
    w, h = im.size
    if min(w, h) < 700:
        sys.exit(f'Photo is too small ({w}x{h}) for the gallery.')

    IMG.mkdir(parents=True, exist_ok=True)
    im.save(IMG / f'work-{slug}.webp', 'WEBP', quality=82, method=6)
    sm = im.resize((SMALL, round(h * SMALL / w)), Image.LANCZOS) if w > SMALL else im
    sm.save(IMG / f'work-{slug}-sm.webp', 'WEBP', quality=80, method=6)

    entry = {'file': slug, 'width': w, 'height': h, 'caption': caption}
    if a.drive_id:
        entry['drive_id'] = a.drive_id
    entry['added'] = datetime.date.today().isoformat()
    block = yaml.safe_dump([entry], sort_keys=False, allow_unicode=True, width=200)
    # insert as the first item under "photos:" so the comments at the top of the file are kept
    new_text, count = re.subn(r'^photos:\n', lambda m: m.group(0) + block, text, count=1, flags=re.M)
    if not count:
        sys.exit('content/gallery.yml: no "photos:" list found.')
    DATA.write_text(new_text)
    print(f'Added work-{slug}.webp ({w}x{h}) "{caption}" to the top of the gallery.')


if __name__ == '__main__':
    main()
