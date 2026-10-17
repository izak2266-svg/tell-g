#!/usr/bin/env python3
"""בוט דילים לטלגרם: אוסף דילים של ביגוד והנעלה ומעלה לערוץ רק דילים קיצוניים עם משלוח לישראל."""
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).parent
SEEN_FILE = ROOT / "seen.json"
UA = "Mozilla/5.0 (compatible; tell-g-deals-bot/1.0)"

CLOTHING = re.compile(
    r"\b(shirt|t-shirt|tee|jeans|pants|trousers|shorts|dress|skirt|jacket|coat|hoodie|"
    r"sweater|sweatshirt|cardigan|blazer|suit|underwear|bra|socks|leggings|swimsuit|"
    r"pajamas?|sneakers?|shoes?|boots?|sandals?|apparel|clothing|clothes|outerwear|"
    r"polo|joggers?|activewear|romper|jumpsuit|bag|backpack)\b|"
    r"חולצ|מכנס|שמלה|חצאית|ג'קט|מעיל|סוודר|הלבשה|ביגוד|נעל|סנדל|בגד",
    re.I,
)
KIDS = re.compile(r"\b(kids?|boys?|girls?|toddler|baby|children|youth)\b|ילד|ילדים|תינוק", re.I)
WOMEN = re.compile(r"\b(women'?s?|womens|ladies|female|girls?)\b|נשים|גברת", re.I)
MEN = re.compile(r"\b(men'?s?|mens|male|boys?)\b|גברים", re.I)
NO_ISRAEL = re.compile(r"\b(us only|usa only|us shipping only|us residents|uk only|eu only)\b", re.I)
ISRAEL_OK = re.compile(r"israel|ישראל|worldwide|ships? internationally", re.I)
PCT = re.compile(r"(\d{2,3})\s*%\s*(?:off|הנחה|discount)|(?:הנחה של|up to|עד)\s*(\d{2,3})\s*%", re.I)
PRICE_PAIR = re.compile(
    r"[$₪€£]\s?(\d+(?:\.\d+)?)[^$₪€£\d]{0,30}?(?:was|from|reg(?:ular)?|msrp|במקום)\D{0,6}[$₪€£]?\s?(\d+(?:\.\d+)?)",
    re.I,
)
URL_RE = re.compile(r'https?://[^\s"\'<>]+')


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def strip_tags(text):
    return html.unescape(re.sub(r"<[^>]+>", " ", text or "")).strip()


def parse_feed(xml_bytes):
    """מחזיר רשימת דילים (title, link, desc, image, id) מ-RSS או Atom."""
    root = ET.fromstring(xml_bytes)
    items = []
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        d = {"title": "", "link": "", "desc": "", "image": "", "id": ""}
        for ch in el:
            t = ch.tag.split("}")[-1]
            if t == "title":
                d["title"] = strip_tags(ch.text)
            elif t == "link":
                d["link"] = ch.get("href") or (ch.text or "").strip()
            elif t in ("description", "summary", "content", "encoded"):
                d["desc"] += " " + (ch.text or "")
            elif t == "guid" or t == "id":
                d["id"] = (ch.text or "").strip()
            elif t in ("thumbnail", "content", "enclosure") and ch.get("url"):
                d["image"] = ch.get("url")
        img = re.search(r'<img[^>]+src="([^"]+)"', d["desc"])
        if not d["image"] and img:
            d["image"] = html.unescape(img.group(1))
        d["id"] = d["id"] or d["link"]
        items.append(d)
    return items


def deal_url(d):
    """מחפש בתיאור קישור ישיר לחנות; אחרת משתמש בקישור הפיד."""
    for u in URL_RE.findall(html.unescape(d["desc"])):
        host = urllib.parse.urlparse(u).netloc.lower()
        if re.search(r"\.(jpe?g|png|gif|webp)(\?|$)", u, re.I):
            continue
        if not any(x in host for x in ("reddit.com", "redd.it", "slickdeals.net", "imgur", "preview.")):
            return u
    return d["link"]


def discount_percent(text):
    best = 0
    for m in PCT.finditer(text):
        best = max(best, int(m.group(1) or m.group(2)))
    for m in PRICE_PAIR.finditer(text):
        now, old = float(m.group(1)), float(m.group(2))
        if old > now > 0:
            best = max(best, round((1 - now / old) * 100))
    return best


def host_of(url):
    return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")


def ships_to_israel(text, url, domains):
    if NO_ISRAEL.search(text):
        return False
    host = host_of(url)
    return bool(ISRAEL_OK.search(text)) or any(host == d or host.endswith("." + d) for d in domains)


def audience(text):
    tags = []
    if MEN.search(text) and not re.search(r"\bwomen", text, re.I):
        tags.append("#גברים")
    if WOMEN.search(text):
        tags.append("#נשים")
    if KIDS.search(text):
        tags.append("#ילדים")
    return tags or ["#לכולם"]


def affiliate_link(url, env=os.environ):
    """מוסיף מזהה שותפים: Amazon tag, או תבנית AFFILIATE_TEMPLATE_<DOMAIN> עם {url}."""
    host = host_of(url)
    if "amazon." in host and env.get("AMAZON_TAG"):
        q = urllib.parse.urlparse(url)
        params = dict(urllib.parse.parse_qsl(q.query))
        params["tag"] = env["AMAZON_TAG"]
        return q._replace(query=urllib.parse.urlencode(params)).geturl()
    for key, tpl in env.items():
        if key.startswith("AFFILIATE_TEMPLATE_") and tpl:
            domain = key.removeprefix("AFFILIATE_TEMPLATE_").lower().replace("_", ".")
            if host == domain or host.endswith("." + domain):
                return tpl.replace("{url}", urllib.parse.quote(url, safe=""))
    return url


def evaluate(d, cfg, env=os.environ):
    """מחזיר דיל מוכן לפרסום או None."""
    text = f"{d['title']} {strip_tags(d['desc'])}"
    if not CLOTHING.search(text):
        return None
    pct = discount_percent(text)
    if pct < cfg["min_discount_percent"]:
        return None
    url = deal_url(d)
    if not ships_to_israel(text, url, cfg["ships_to_israel_domains"]):
        return None
    return {"title": d["title"], "pct": min(pct, 99), "url": affiliate_link(url, env),
            "image": d["image"], "tags": audience(text), "store": host_of(url)}


def format_message(deal):
    return (
        f"🔥 <b>דיל קיצוני: {deal['pct']}% הנחה!</b>\n\n"
        f"{html.escape(deal['title'])}\n\n"
        f"🏬 {html.escape(deal['store'])}\n"
        f"🚚 משלוח לישראל\n"
        f'👉 <a href="{html.escape(deal["url"], quote=True)}">לדיל</a>\n\n'
        f"{' '.join(deal['tags'])}"
    )


def telegram(method, token, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}", data=data,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def post(deal, token, chat_id):
    text = format_message(deal)
    if deal["image"] and len(text) < 1000:
        try:
            telegram("sendPhoto", token, {"chat_id": chat_id, "photo": deal["image"],
                                          "caption": text, "parse_mode": "HTML"})
            return
        except Exception as e:  # תמונה לא תקינה: שולחים טקסט בלבד
            print("sendPhoto failed, falling back:", e, file=sys.stderr)
    telegram("sendMessage", token, {"chat_id": chat_id, "text": text, "parse_mode": "HTML"})


def main():
    cfg = load_json(ROOT / "sources.json", {})
    seen = set(load_json(SEEN_FILE, []))
    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    dry = not (token and chat_id)
    posted = 0
    for feed in cfg["feeds"]:
        try:
            items = parse_feed(fetch(feed["url"]))
        except Exception as e:
            print(f"[{feed['name']}] failed: {e}", file=sys.stderr)
            continue
        for d in items:
            if d["id"] in seen:
                continue
            seen.add(d["id"])
            deal = evaluate(d, cfg)
            if not deal or posted >= cfg["max_posts_per_run"]:
                continue
            if dry:
                print(format_message(deal), "\n---")
            else:
                post(deal, token, chat_id)
            posted += 1
    SEEN_FILE.write_text(json.dumps(sorted(seen)[-5000:], ensure_ascii=False), encoding="utf-8")
    print(f"posted {posted} deals{' (dry run)' if dry else ''}")


if __name__ == "__main__":
    main()
