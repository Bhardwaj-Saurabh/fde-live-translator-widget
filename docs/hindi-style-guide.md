# Hindi Style Guide — how real Hindi web writing works

The source of truth for this product's English → Hindi (hi-IN) translation
style. Synthesized from primary research on high-traffic Hindi blogs, major
news portals, live e-commerce Hindi UIs, and authoritative localization
guides (July 2026). The translator prompt in
`backend/ai-service-python/lib/llm.py` is a **distillation of this guide —
when you change one, change both.**

A convention entered this guide only if confirmed by ≥3 independent sources,
or 2 sources plus an authority guide. Where the wild genuinely disagrees, the
split is recorded and our default is stated with its rationale.

## 1. Purpose & sources

LLMs translate English into a Hindi that reads *translated* — over-formal,
sanskritized, literal in word order. Real high-follower Hindi web writing is
different, and this guide captures how.

**Blogs (9 articles):** ShoutMeHindi, HindiMeHelp, AchhiKhabar, SupportMeIndia.
**News portals (7 articles):** Aaj Tak, Amar Ujala, TV9 Hindi (Jagran/Bhaskar/NDTV blocked automated access — spot-check manually if precision matters).
**E-commerce UI:** Amazon.in Hindi interface (help pages = canonical strings), Flipkart Hindi homepage.
**Authorities:** Mozilla hi-IN l10n guide, Hindi Wikipedia Manual of Style, Unicode CLDR (hi), W3C/r12a Hindi orthography notes, Google Material Design language guidance. (Microsoft Hindi Style Guide PDF exists but wasn't machine-readable — its rows are unverified.)

Retrieved 2026-07-12. Patterns and short illustrative phrases only — no source paragraphs are reproduced here.

## 2. Register & audience

- **Modern web Hindi** ("blog Hindi"), not shuddh/literary Hindi and not
  romanized Hinglish. Conversational but respectful.
- **Always आप**, never तुम/तू. All four blogs and every UI string agree.
- **Imperatives in the करें/-एं form**: खरीदें, खोजें, जोड़ें, जारी रखें.
  This is the modern UI standard (Mozilla mandates it; Amazon/Flipkart use it
  exclusively). कीजिए appears in blog prose as extra politeness but never in
  UI; करो is informal register drift — never use either in output.
- News body sentences run ~12–18 words; blogs are similar with more direct
  reader address. Split long English sentences rather than mirroring them.

## 3. Loanword policy — the core pattern

Real Hindi web writing keeps English **nouns** as Devanagari loanwords and
uses **native Hindi verbs and value-words** around them. The canonical hybrid:
**कार्ट में जोड़ें** (loan noun + native verb).

**Keep as Devanagari English loans** (observed across blogs, news, UIs):
कार्ट, चेकआउट, ऑर्डर, डिलीवरी, अकाउंट, प्रोडक्ट, स्टॉक, सेल, रेटिंग,
रिटर्न पॉलिसी, विशलिस्ट, लोकेशन, ऐप, वेबसाइट, ब्लॉग, इंटरनेट, मोबाइल,
स्मार्टफोन, बैटरी, डिस्प्ले, डेटा, ऑनलाइन, ईमेल, पुलिस, बैंक, टीम,
टेक्नोलॉजी, फ्री (competes with मुफ़्त — both fine), पिन, सिक्योरिटी.

**Translate to native Hindi** (natural everyday words exist):
buy → खरीदें · search → खोजें/ढूंढें · price → कीमत/दाम · discount → छूट ·
payment → भुगतान · reviews → समीक्षाएं · help → मदद · continue → जारी रखें ·
cancel → रद्द करें · choose → चुनें · add → जोड़ें · free → मुफ़्त ·
offer → ऑफ़र (loan) but "special offer" → खास ऑफ़र.

Blog loanword density runs roughly 15–20% of words in tech content, lower in
general prose. Don't force a native coinage where the loan is what people
actually say — and don't import an English word where the native word is
universal (see anti-patterns, §8).

## 4. Script rules — what stays in Latin

Keep in **Latin script, exactly as in the source** (strong consensus:
Mozilla "never localize/transliterate brand names", Wikipedia, every news
portal):

- **Brand & product names:** Home Depot, Google, Apple, iPhone 18 Pro, DeWalt.
  (गूगल/ऐपल transliterations exist in the wild but Latin dominates — we
  standardize on Latin.)
- **Model/SKU codes:** WH-1000XM5, T5 Pro 5G, SKU-4471.
- **Acronyms:** SEO, URL, OTP, AI, GPS, LED. (Very familiar Indian ones like
  एफआईआर appear transliterated in news; we keep acronyms Latin for
  consistency.)
- **Units & specs attached to numbers:** 1.5GB, 44W, 7200mAh, 4K.
- **URLs, emails, HTML tags/entities, code.**

Everything else is **Devanagari**. Never output romanized Hinglish
("aap kart mein jodein" is an automatic style fail).

## 5. Numerals, currency & punctuation

- **Digits: Western 0-9, always.** Devanagari digits (१२३) were never
  observed in 16 sampled articles across blogs and news; CLDR's default
  numbering for hi is `latn`; Mozilla mandates 0-9. Never output ०-९.
- **Grouping:** Indian 2-2-3 style where the source is Indian-formatted
  (35,999; 1,00,000) — but **never reformat numbers that appear in the
  source; copy them verbatim.**
- **Large numbers in prose:** लाख/करोड़, never "मिलियन" (news consensus).
- **Currency: preserve the source symbol and amount exactly.** $1,299.00
  stays $1,299.00 — never convert to ₹, never respell. (Native convention is
  ₹499 in headlines / "3000 रुपये" in body, which matters only for
  Hindi-native content, not for translations of a US site.)
- **Percentages:** keep the % symbol with the digit ("25% छूट").
- **Sentence-final punctuation — the danda verdict:** the wild is genuinely
  split (general news + literary blogs use danda ।; tech desks and how-to
  blogs drift to western period, sometimes mixed in one article). **Our
  default: danda । for prose sentences** — it's what every authority
  (Mozilla, W3C) prescribes and what hard news does. No space before danda,
  one space after. Never the ASCII pipe `|`.
- **UI fragments (labels, buttons, nav, headings) get NO terminal
  punctuation** — observed universally on Amazon/Flipkart Hindi.
- **Quotes:** straight double quotes "…" for quoted matter; single quotes
  for emphasis/scare-quotes (news headline style). No guillemets.
- **Dates:** "12 जुलाई 2026" — Arabic day + Hindi month + year, no ordinal.

## 6. UI-microcopy lexicon (verified strings)

Canonical renderings from live Amazon.in Hindi / Flipkart Hindi surfaces.
Use these exact strings when the source text matches; they also set the
pattern for unlisted labels. Confidence: H = seen on live surface/help
title, M = attested in help text/articles, L = inferred (verify before
relying).

| English | Hindi | Conf |
|---|---|---|
| Add to cart | कार्ट में जोड़ें | M-H |
| Buy now | अभी खरीदें | H |
| Checkout | चेकआउट | H |
| Proceed to checkout | चेकआउट करने के लिए आगे बढ़ें | H |
| Place order | अपना ऑर्डर दें | H |
| Search | खोजें (Flipkart search box: प्रोडक्ट ढूंढें) | H |
| Sign in / Log in | साइन इन करें / लॉगिन करें | H |
| My account | मेरा अकाउंट | H |
| My orders | मेरे ऑर्डर | M-H |
| Wishlist | विशलिस्ट | M-H |
| Free delivery | मुफ़्त डिलीवरी | H |
| Out of stock | स्टॉक में नहीं है | H |
| In stock | स्टॉक में है | M |
| Price | कीमत | H |
| Discount / % off | छूट / % छूट | H |
| Sale | सेल | H |
| Reviews | समीक्षाएं | H |
| Ratings | रेटिंग | H |
| Return policy | रिटर्न पॉलिसी | H |
| Track order | अपना ऑर्डर ट्रैक करें | H |
| Payment | भुगतान | H |
| Home (nav) | होम | L-M |
| Continue | जारी रखें | H |
| Cancel | रद्द करें | M |
| Submit | सबमिट करें | L |
| Help | मदद | H |
| Choose delivery location | डिलीवरी लोकेशन चुनें | H |

Category labels: मोबाइल · फ़ैशन · घर और किचन · किताबें · इलेक्ट्रॉनिक्स.

## 7. Sentence rhythm & structure

- Natural Hindi SOV order — restructure, don't mirror English word order.
  "Get 25% off on all power tools" → "सभी पावर टूल्स पर 25% छूट पाएं",
  not a word-by-word gloss.
- Prefer two short sentences over one long nested one; body sentences
  ~12–18 words read as native news/blog register.
- Blogs address the reader directly (questions, "तो चलिए…", "दोस्तों") —
  fine to preserve the source's tone, but never *add* conversational devices
  the source doesn't have.
- Latin brand tokens sit naturally inside Devanagari clauses:
  "Vivo के दो पॉपुलर 5G फोन" — don't quarantine or gloss them.

## 8. Anti-patterns — what LLMs get wrong

These are the failures this guide exists to prevent. Each is a style fail:

1. **Over-sanskritized coinage** where a loan is universal:
   अनुप्रयोग → ऐप · अंतरजाल → इंटरनेट · संगणक → कंप्यूटर ·
   दूरभाष → फ़ोन · क्रय करें → खरीदें · टोकरी → कार्ट.
2. **Literal word order** mirroring English syntax.
3. **Translating/transliterating brand names** (होम डिपो ✗ → Home Depot ✓).
4. **Preambles or wrappers**: "अनुवाद:", "यहाँ अनुवाद है", wrapping quotes,
   trailing notes. Output is the translation and nothing else.
5. **Devanagari digits** (१२३) anywhere.
6. **Converting currency** ($49.99 → ₹4,150 ✗) or reformatting numbers.
7. **Romanized Hinglish output** (Latin-script Hindi words).
8. **Adding terminal punctuation to UI labels**, or a period where prose
   needs danda.
9. **कीजिए/करो imperatives** in UI strings (standard is करें).
10. **Translating untranslatable tokens**: SKUs, units (7200mAh), HTML
    entities (&amp;), emoji — all pass through verbatim.

## 9. Canonical few-shot pairs

The prompt's examples in `lib/llm.py` derive from these — **keep in sync**.
Freshly authored against §2–§8 (not copied from any source; kept distinct
from test inputs to avoid echo). Tags: `ui` = fragment, no terminal
punctuation; `product` = commerce copy; `prose` = full sentences, danda.

| # | Tag | English | Hindi |
|---|-----|---------|-------|
| 1 | ui | View all deals | सभी डील देखें |
| 2 | ui | Free shipping on orders over $45 | $45 से ज़्यादा के ऑर्डर पर मुफ़्त शिपिंग |
| 3 | ui | Remove from wishlist | विशलिस्ट से हटाएं |
| 4 | product | DeWalt 20V MAX Drill, Model DCD771C2 — now $99.00 (was $159.00) | DeWalt 20V MAX ड्रिल, मॉडल DCD771C2 — अभी $99.00 (पहले $159.00) |
| 5 | product | Save 30% on select ceiling fans. Offer ends July 15. | चुनिंदा सीलिंग फैन पर 30% बचाएं। ऑफ़र 15 जुलाई को खत्म होगा। |
| 6 | prose | Your package will arrive within 5 business days. | आपका पैकेज 5 कारोबारी दिनों में पहुंच जाएगा। |
| 7 | prose | We couldn't process your payment. Please try a different card. | हम आपका भुगतान प्रोसेस नहीं कर पाए। कृपया कोई दूसरा कार्ड आज़माएं। |
| 8 | prose | This washing machine has a 4.5-star rating from over 2,000 customers. | इस वॉशिंग मशीन को 2,000 से ज़्यादा ग्राहकों ने 4.5-स्टार रेटिंग दी है। |
| 9 | ui | Sign in to see your saved items | अपने सेव किए आइटम देखने के लिए साइन इन करें |
| 10 | prose | Compare prices before you buy — it only takes a minute. | खरीदने से पहले कीमतों की तुलना करें — इसमें बस एक मिनट लगता है। |

The prompt carries a **trimmed subset** (#2, #4, #7 — one per tag) since every
few-shot token rides on every cache miss; the full table remains the review
reference. **Few-shot backfire warning:** a bare `Home → होम` example taught
the model to transliterate "Home Depot" — single-word examples that prefix
brand names don't belong in few-shot; encode that case as a *rule* (§6.1).

### 6.1 Nav labels & mixed input (additions)

- **Single-word nav labels take their website sense:** Home → होम,
  Cart → कार्ट, About → हमारे बारे में. (Rule, not few-shot — see warning above.)
- **Mixed Hindi/English input:** text already in Devanagari is kept verbatim;
  only the English parts are translated. (Real pages served to Indian users
  often arrive half-localized.)

## 10. Maintenance

- **Prompt ↔ guide sync:** `_STYLE_BLOCKS["hi-IN"]` and `_FEW_SHOT["hi-IN"]`
  in `lib/llm.py` are distilled from §2–§9. Any change here must be
  reflected there (and vice versa), and the live style tests re-run.
- **Token budget:** the distilled block + few-shot cost ~730 prompt tokens per
  cache miss (measured via OpenRouter `usage`, 2026-07-13; was ~1140 before
  compression). When adding rules, prefer editing/merging bullets over
  appending, and re-measure.
- **Cache staleness:** the cache key is `(text, target)` with no prompt
  version — after any prompt revision, delete `translations.db` (and restart)
  or old-style translations will keep being served.
- **Model changes:** re-run `RUN_LIVE_LLM_TESTS=1 pytest -m live` whenever
  `MODEL` changes; style adherence drifts across models.
- **Text expansion:** Hindi renders ~15–30% longer than English and needs
  more line height (tall script) — a widget-layout consideration, not a
  backend one.
- **Open questions from research:** % vs फीसदी in prose (unconfirmed);
  कार्ट में जोड़ें vs कार्ट में डालें live-button split; Jagran/Bhaskar/NDTV
  conventions unverified (fetch-blocked).
