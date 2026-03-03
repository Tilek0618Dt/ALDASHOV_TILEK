# app/data/countries.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple, Dict, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# =========================
# Data models
# =========================
@dataclass(frozen=True)
class Country:
    code: str   # ISO 3166-1 alpha-2
    name: str   # display name


@dataclass(frozen=True)
class Language:
    code: str   # BCP-47-ish (we keep simple)
    name: str   # display name


# =========================
# Countries (100+)
# =========================
COUNTRIES: List[Country] = [
    Country("KG", "🇰🇬 Kyrgyzstan / Кыргызстан"),
    Country("RU", "🇷🇺 Russia / Россия"),
    Country("KZ", "🇰🇿 Kazakhstan / Казахстан"),
    Country("UZ", "🇺🇿 Uzbekistan / Oʻzbekiston"),
    Country("TJ", "🇹🇯 Tajikistan / Тоҷикистон"),
    Country("TM", "🇹🇲 Turkmenistan / Türkmenistan"),
    Country("AZ", "🇦🇿 Azerbaijan / Azərbaycan"),
    Country("GE", "🇬🇪 Georgia / საქართველო"),
    Country("AM", "🇦🇲 Armenia / Հայաստան"),
    Country("TR", "🇹🇷 Türkiye"),
    Country("UA", "🇺🇦 Ukraine"),
    Country("BY", "🇧🇾 Belarus"),
    Country("MD", "🇲🇩 Moldova"),
    Country("LV", "🇱🇻 Latvia"),
    Country("LT", "🇱🇹 Lithuania"),
    Country("EE", "🇪🇪 Estonia"),
    Country("PL", "🇵🇱 Poland"),
    Country("CZ", "🇨🇿 Czechia"),
    Country("SK", "🇸🇰 Slovakia"),
    Country("HU", "🇭🇺 Hungary"),
    Country("RO", "🇷🇴 Romania"),
    Country("BG", "🇧🇬 Bulgaria"),
    Country("GR", "🇬🇷 Greece"),
    Country("RS", "🇷🇸 Serbia"),
    Country("HR", "🇭🇷 Croatia"),
    Country("SI", "🇸🇮 Slovenia"),
    Country("BA", "🇧🇦 Bosnia & Herzegovina"),
    Country("ME", "🇲🇪 Montenegro"),
    Country("MK", "🇲🇰 North Macedonia"),
    Country("AL", "🇦🇱 Albania"),
    Country("IT", "🇮🇹 Italy"),
    Country("ES", "🇪🇸 Spain"),
    Country("PT", "🇵🇹 Portugal"),
    Country("FR", "🇫🇷 France"),
    Country("DE", "🇩🇪 Germany"),
    Country("AT", "🇦🇹 Austria"),
    Country("CH", "🇨🇭 Switzerland"),
    Country("NL", "🇳🇱 Netherlands"),
    Country("BE", "🇧🇪 Belgium"),
    Country("LU", "🇱🇺 Luxembourg"),
    Country("DK", "🇩🇰 Denmark"),
    Country("NO", "🇳🇴 Norway"),
    Country("SE", "🇸🇪 Sweden"),
    Country("FI", "🇫🇮 Finland"),
    Country("IS", "🇮🇸 Iceland"),
    Country("IE", "🇮🇪 Ireland"),
    Country("GB", "🇬🇧 United Kingdom"),
    Country("US", "🇺🇸 United States"),
    Country("CA", "🇨🇦 Canada"),
    Country("MX", "🇲🇽 Mexico"),
    Country("BR", "🇧🇷 Brazil"),
    Country("AR", "🇦🇷 Argentina"),
    Country("CL", "🇨🇱 Chile"),
    Country("CO", "🇨🇴 Colombia"),
    Country("PE", "🇵🇪 Peru"),
    Country("VE", "🇻🇪 Venezuela"),
    Country("EC", "🇪🇨 Ecuador"),
    Country("BO", "🇧🇴 Bolivia"),
    Country("PY", "🇵🇾 Paraguay"),
    Country("UY", "🇺🇾 Uruguay"),
    Country("PA", "🇵🇦 Panama"),
    Country("CR", "🇨🇷 Costa Rica"),
    Country("GT", "🇬🇹 Guatemala"),
    Country("CU", "🇨🇺 Cuba"),
    Country("DO", "🇩🇴 Dominican Republic"),
    Country("HT", "🇭🇹 Haiti"),
    Country("JM", "🇯🇲 Jamaica"),
    Country("AU", "🇦🇺 Australia"),
    Country("NZ", "🇳🇿 New Zealand"),
    Country("JP", "🇯🇵 Japan"),
    Country("KR", "🇰🇷 South Korea"),
    Country("CN", "🇨🇳 China"),
    Country("TW", "🇹🇼 Taiwan"),
    Country("HK", "🇭🇰 Hong Kong"),
    Country("SG", "🇸🇬 Singapore"),
    Country("MY", "🇲🇾 Malaysia"),
    Country("TH", "🇹🇭 Thailand"),
    Country("VN", "🇻🇳 Vietnam"),
    Country("PH", "🇵🇭 Philippines"),
    Country("ID", "🇮🇩 Indonesia"),
    Country("IN", "🇮🇳 India"),
    Country("PK", "🇵🇰 Pakistan"),
    Country("BD", "🇧🇩 Bangladesh"),
    Country("LK", "🇱🇰 Sri Lanka"),
    Country("NP", "🇳🇵 Nepal"),
    Country("AF", "🇦🇫 Afghanistan"),
    Country("IR", "🇮🇷 Iran"),
    Country("IQ", "🇮🇶 Iraq"),
    Country("SY", "🇸🇾 Syria"),
    Country("IL", "🇮🇱 Israel"),
    Country("PS", "🇵🇸 Palestine"),
    Country("JO", "🇯🇴 Jordan"),
    Country("LB", "🇱🇧 Lebanon"),
    Country("SA", "🇸🇦 Saudi Arabia"),
    Country("AE", "🇦🇪 United Arab Emirates"),
    Country("QA", "🇶🇦 Qatar"),
    Country("KW", "🇰🇼 Kuwait"),
    Country("BH", "🇧🇭 Bahrain"),
    Country("OM", "🇴🇲 Oman"),
    Country("YE", "🇾🇪 Yemen"),
    Country("EG", "🇪🇬 Egypt"),
    Country("MA", "🇲🇦 Morocco"),
    Country("DZ", "🇩🇿 Algeria"),
    Country("TN", "🇹🇳 Tunisia"),
    Country("LY", "🇱🇾 Libya"),
    Country("SD", "🇸🇩 Sudan"),
    Country("ET", "🇪🇹 Ethiopia"),
    Country("KE", "🇰🇪 Kenya"),
    Country("TZ", "🇹🇿 Tanzania"),
    Country("UG", "🇺🇬 Uganda"),
    Country("GH", "🇬🇭 Ghana"),
    Country("NG", "🇳🇬 Nigeria"),
    Country("SN", "🇸🇳 Senegal"),
    Country("CM", "🇨🇲 Cameroon"),
    Country("CI", "🇨🇮 Côte d’Ivoire"),
    Country("ZA", "🇿🇦 South Africa"),
    Country("ZW", "🇿🇼 Zimbabwe"),
    Country("ZM", "🇿🇲 Zambia"),
    Country("AO", "🇦🇴 Angola"),
]


# =========================
# Languages (100+)
# =========================
LANGUAGES: List[Language] = [
    Language("ky", "Кыргызча (Kyrgyz)"),
    Language("ru", "Русский (Russian)"),
    Language("kk", "Қазақша (Kazakh)"),
    Language("uz", "Oʻzbekcha (Uzbek)"),
    Language("tg", "Тоҷикӣ (Tajik)"),
    Language("tk", "Türkmençe (Turkmen)"),
    Language("tr", "Türkçe (Turkish)"),
    Language("en", "English"),
    Language("de", "Deutsch"),
    Language("fr", "Français"),
    Language("es", "Español"),
    Language("pt", "Português"),
    Language("it", "Italiano"),
    Language("nl", "Nederlands"),
    Language("sv", "Svenska"),
    Language("no", "Norsk"),
    Language("da", "Dansk"),
    Language("fi", "Suomi"),
    Language("is", "Íslenska"),
    Language("pl", "Polski"),
    Language("cs", "Čeština"),
    Language("sk", "Slovenčina"),
    Language("hu", "Magyar"),
    Language("ro", "Română"),
    Language("bg", "Български"),
    Language("el", "Ελληνικά"),
    Language("sr", "Српски"),
    Language("hr", "Hrvatski"),
    Language("sl", "Slovenščina"),
    Language("uk", "Українська"),
    Language("be", "Беларуская"),
    Language("ar", "العربية"),
    Language("fa", "فارسی"),
    Language("ur", "اردو"),
    Language("hi", "हिन्दी"),
    Language("bn", "বাংলা"),
    Language("pa", "ਪੰਜਾਬੀ"),
    Language("gu", "ગુજરાતી"),
    Language("mr", "मराठी"),
    Language("ta", "தமிழ்"),
    Language("te", "తెలుగు"),
    Language("kn", "ಕನ್ನಡ"),
    Language("ml", "മലയാളം"),
    Language("si", "සිංහල"),
    Language("ne", "नेपाली"),
    Language("zh", "中文"),
    Language("zh-Hant", "中文（繁體）"),
    Language("ja", "日本語"),
    Language("ko", "한국어"),
    Language("vi", "Tiếng Việt"),
    Language("th", "ไทย"),
    Language("id", "Bahasa Indonesia"),
    Language("ms", "Bahasa Melayu"),
    Language("tl", "Tagalog"),
    Language("sw", "Kiswahili"),
    Language("am", "አማርኛ (Amharic)"),
    Language("ha", "Hausa"),
    Language("yo", "Yorùbá"),
    Language("ig", "Igbo"),
    Language("zu", "isiZulu"),
    Language("xh", "isiXhosa"),
    Language("af", "Afrikaans"),
    Language("he", "עברית"),
    Language("ps", "پښتو"),
    Language("ku", "Kurdî (Kurdish)"),
    Language("az", "Azərbaycanca"),
    Language("hy", "Հայերեն"),
    Language("ka", "ქართული"),
    Language("et", "Eesti"),
    Language("lv", "Latviešu"),
    Language("lt", "Lietuvių"),
    Language("mt", "Malti"),
    Language("ga", "Gaeilge"),
    Language("cy", "Cymraeg"),
    Language("gd", "Gàidhlig"),
    Language("eo", "Esperanto"),
    Language("la", "Latina"),
    Language("sq", "Shqip"),
    Language("mk", "Македонски"),
    Language("bs", "Bosanski"),
    Language("mn", "Монгол"),
    Language("my", "မြန်မာ (Burmese)"),
    Language("km", "ភាសាខ្មែរ (Khmer)"),
    Language("lo", "ລາວ (Lao)"),
    Language("dv", "ދިވެހި (Dhivehi)"),
    Language("so", "Soomaali"),
    Language("om", "Afaan Oromoo"),
    Language("rw", "Kinyarwanda"),
    Language("rn", "Kirundi"),
    Language("mg", "Malagasy"),
    Language("sn", "Shona"),
    Language("st", "Sesotho"),
    Language("tn", "Setswana"),
    Language("ts", "Xitsonga"),
    Language("ny", "Chichewa"),
    Language("ceb", "Cebuano"),
    Language("jv", "Basa Jawa"),
    Language("su", "Basa Sunda"),
    Language("eu", "Euskara"),
    Language("ca", "Català"),
    Language("gl", "Galego"),
    Language("oc", "Occitan"),
    Language("sc", "Sardu"),
    Language("lb", "Lëtzebuergesch"),
    Language("fo", "Føroyskt"),
    Language("mi", "Māori"),
    Language("haw", "ʻŌlelo Hawaiʻi"),
    Language("sm", "Gagana Samoa"),
    Language("to", "Lea Faka-Tonga"),
    Language("fj", "Vosa Vakaviti"),
]


# =========================
# Fast lookup
# =========================
_COUNTRY_BY_CODE: Dict[str, Country] = {c.code.upper(): c for c in COUNTRIES}
_LANG_BY_CODE: Dict[str, Language] = {l.code: l for l in LANGUAGES}


def get_country(code: str) -> Optional[Country]:
    return _COUNTRY_BY_CODE.get((code or "").upper())


def get_language(code: str) -> Optional[Language]:
    return _LANG_BY_CODE.get(code or "")


# =========================
# UI helpers (Inline keyboards with paging)
# =========================
def _chunk(items: List, size: int) -> List[List]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def kb_countries(page: int = 0, per_page: int = 12) -> InlineKeyboardMarkup:
    """
    callback_data: set:country:KG
    paging: nav:country:prev / nav:country:next
    """
    items = COUNTRIES[:]
    pages = _chunk(items, per_page)
    if not pages:
        pages = [[]]
    page = max(0, min(page, len(pages) - 1))

    rows = []
    for c in pages[page]:
        rows.append([InlineKeyboardButton(text=c.name, callback_data=f"set:country:{c.code}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Артка", callback_data="nav:country:prev"))
    nav.append(InlineKeyboardButton(text=f"📍 Барак {page+1}/{len(pages)}", callback_data="noop"))
    if page < len(pages) - 1:
        nav.append(InlineKeyboardButton(text="➡️ Кийинки", callback_data="nav:country:next"))

    rows.append(nav)
    rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="m:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_languages(page: int = 0, per_page: int = 12) -> InlineKeyboardMarkup:
    """
    callback_data: set:lang:ky
    paging: nav:lang:prev / nav:lang:next
    """
    items = LANGUAGES[:]
    pages = _chunk(items, per_page)
    if not pages:
        pages = [[]]
    page = max(0, min(page, len(pages) - 1))

    rows = []
    for l in pages[page]:
        rows.append([InlineKeyboardButton(text=l.name, callback_data=f"set:lang:{l.code}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Артка", callback_data="nav:lang:prev"))
    nav.append(InlineKeyboardButton(text=f"🌐 Барак {page+1}/{len(pages)}", callback_data="noop"))
    if page < len(pages) - 1:
        nav.append(InlineKeyboardButton(text="➡️ Кийинки", callback_data="nav:lang:next"))

    rows.append(nav)
    rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="m:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pretty_profile(country_code: Optional[str], lang_code: Optional[str]) -> str:
    c = get_country(country_code or "") if country_code else None
    l = get_language(lang_code or "") if lang_code else None
    c_text = c.name if c else "—"
    l_text = l.name if l else "—"
    return f"📍 Өлкө: {c_text}\n🌐 Тил: {l_text}"
