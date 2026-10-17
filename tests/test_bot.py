import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import bot

CFG = {"min_discount_percent": 50, "ships_to_israel_domains": ["aliexpress.com", "asos.com"]}
RSS = b"""<rss><channel>
<item><title>Men's Hoodie 60% off at ASOS</title><guid>1</guid>
<description>&lt;img src="http://x/i.jpg"&gt; &lt;a href="https://www.asos.com/p/1"&gt;buy&lt;/a&gt;</description><link>http://f/1</link></item>
<item><title>Women's dress $10 (was $40) US only</title><guid>2</guid><description>https://www.asos.com/p/2</description></item>
<item><title>Laptop 70% off</title><guid>3</guid><description>https://www.asos.com/p/3</description></item>
<item><title>Kids shoes 20% off</title><guid>4</guid><description>https://www.asos.com/p/4</description></item>
</channel></rss>"""

class T(unittest.TestCase):
    def test_pipeline(self):
        items = bot.parse_feed(RSS)
        res = [bot.evaluate(i, CFG, {}) for i in items]
        self.assertEqual(res[0]["pct"], 60)
        self.assertEqual(res[0]["store"], "asos.com")
        self.assertEqual(res[0]["tags"], ["#גברים"])
        self.assertEqual(res[0]["image"], "http://x/i.jpg")
        self.assertIsNone(res[1])  # US only
        self.assertIsNone(res[2])  # לא ביגוד
        self.assertIsNone(res[3])  # הנחה קטנה
    def test_price_pair(self):
        self.assertEqual(bot.discount_percent("Dress $10 (was $40)"), 75)
    def test_affiliate(self):
        self.assertIn("tag=me-20", bot.affiliate_link("https://www.amazon.com/dp/X", {"AMAZON_TAG": "me-20"}))
        out = bot.affiliate_link("https://www.aliexpress.com/item/1", {"AFFILIATE_TEMPLATE_ALIEXPRESS_COM": "https://s.click/?u={url}"})
        self.assertTrue(out.startswith("https://s.click/?u=https%3A"))
    def test_message(self):
        d = bot.evaluate(bot.parse_feed(RSS)[0], CFG, {})
        self.assertIn("60%", bot.format_message(d))
unittest.main()
