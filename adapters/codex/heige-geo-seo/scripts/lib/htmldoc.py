"""Parse an HTML document into a structured form for GEO scoring.

Pure stdlib (html.parser). No network, no third-party deps.
"""

import re
from html.parser import HTMLParser


_SKIP_TEXT_TAGS = {"script", "style", "noscript", "template"}
_BLOCK_BREAK_TAGS = {"p", "br", "div", "section", "article", "li", "tr", "h1",
                     "h2", "h3", "h4", "h5", "h6"}


class _DocParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self._in_title = False

        self.meta = {}            # name/property -> content
        self.canonical = None

        self.headings = []        # list of (level, text)
        self._heading_level = 0
        self._heading_parts = []

        self.counts = {"ul": 0, "ol": 0, "table": 0, "li": 0, "th": 0,
                       "dl": 0, "details": 0, "strong": 0, "img": 0,
                       "img_with_alt": 0, "script": 0, "div": 0}

        self.jsonld_blocks = []   # raw JSON strings
        self._in_jsonld = False
        self._jsonld_parts = []

        self.links = []           # list of dicts: href, rel, text
        self._cur_link = None
        self._cur_link_text = []

        self.time_attrs = []      # datetime attr values + text
        self._in_time = False
        self._time_parts = []
        self._time_attr = None

        self.text_parts = []      # visible text
        self._skip_depth = 0

        self.has_rel_author = False
        self.lang = None

    # -- helpers -------------------------------------------------------
    def _attr(self, attrs, key):
        for k, v in attrs:
            if k == key:
                return v if v is not None else ""
        return None

    # -- tag handlers --------------------------------------------------
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.counts:
            self.counts[tag] += 1

        if tag in _SKIP_TEXT_TAGS:
            self._skip_depth += 1

        if tag == "html":
            lang = self._attr(attrs, "lang")
            if lang:
                self.lang = lang

        if tag == "title":
            self._in_title = True

        if tag == "meta":
            name = self._attr(attrs, "name") or self._attr(attrs, "property")
            content = self._attr(attrs, "content")
            if name is not None and content is not None:
                self.meta[name.lower()] = content

        if tag == "link":
            rel = (self._attr(attrs, "rel") or "").lower()
            href = self._attr(attrs, "href")
            if rel == "canonical" and href:
                self.canonical = href
            if rel == "author":
                self.has_rel_author = True

        if tag == "img":
            alt = self._attr(attrs, "alt")
            if alt:
                self.counts["img_with_alt"] += 1

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading_level = int(tag[1])
            self._heading_parts = []

        if tag == "script":
            t = (self._attr(attrs, "type") or "").lower()
            if t == "application/ld+json":
                self._in_jsonld = True
                self._jsonld_parts = []

        if tag == "a":
            href = self._attr(attrs, "href")
            rel = (self._attr(attrs, "rel") or "").lower()
            self._cur_link = {"href": href or "", "rel": rel}
            self._cur_link_text = []
            if "author" in rel:
                self.has_rel_author = True

        if tag == "time":
            self._in_time = True
            self._time_parts = []
            self._time_attr = self._attr(attrs, "datetime")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _SKIP_TEXT_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

        if tag == "title":
            self._in_title = False

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            text = "".join(self._heading_parts).strip()
            if text:
                self.headings.append((int(tag[1]), text))
            self._heading_level = 0
            self._heading_parts = []

        if tag == "script" and self._in_jsonld:
            self.jsonld_blocks.append("".join(self._jsonld_parts).strip())
            self._in_jsonld = False
            self._jsonld_parts = []

        if tag == "a" and self._cur_link is not None:
            self._cur_link["text"] = "".join(self._cur_link_text).strip()
            self.links.append(self._cur_link)
            self._cur_link = None
            self._cur_link_text = []

        if tag == "time" and self._in_time:
            self.time_attrs.append({
                "datetime": self._time_attr,
                "text": "".join(self._time_parts).strip(),
            })
            self._in_time = False
            self._time_parts = []
            self._time_attr = None

        if tag in _BLOCK_BREAK_TAGS:
            self.text_parts.append("\n")

    def handle_data(self, data):
        if self._in_jsonld:
            self._jsonld_parts.append(data)
            return
        if self._in_title:
            self.title_parts.append(data)
        if self._heading_level:
            self._heading_parts.append(data)
        if self._cur_link is not None:
            self._cur_link_text.append(data)
        if self._in_time:
            self._time_parts.append(data)
        # title 文本单独进 doc.title,不混入正文 text(否则会漏进首段、污染段落计数和要素标注)
        if self._skip_depth == 0 and not self._in_title:
            self.text_parts.append(data)


class HtmlDoc:
    """Structured view over a parsed HTML document."""

    def __init__(self, html):
        p = _DocParser()
        p.feed(html or "")
        p.close()
        self.raw = html or ""
        self.title = re.sub(r"\s+", " ", "".join(p.title_parts)).strip()
        self.meta = p.meta
        self.canonical = p.canonical
        self.headings = p.headings
        self.counts = p.counts
        self.jsonld_blocks = p.jsonld_blocks
        self.links = p.links
        self.time_attrs = p.time_attrs
        self.has_rel_author = p.has_rel_author
        self.lang = p.lang
        self.text = self._clean_text(p.text_parts)

    @staticmethod
    def _clean_text(parts):
        raw = "".join(parts)
        lines = [ln.strip() for ln in raw.split("\n")]
        lines = [ln for ln in lines if ln]
        return "\n".join(lines)

    # -- derived metrics ----------------------------------------------
    @property
    def visible_text_len(self):
        return len(self.text.replace("\n", ""))

    @property
    def is_cjk(self):
        cjk = len(re.findall(r"[一-鿿]", self.text))
        latin = len(re.findall(r"[A-Za-z]", self.text))
        return cjk >= latin

    def word_count(self):
        """Approximate word count. CJK chars counted individually,
        latin runs counted as words. Good enough for band thresholds."""
        cjk = len(re.findall(r"[一-鿿]", self.text))
        latin_words = len(re.findall(r"[A-Za-z][A-Za-z'-]*", self.text))
        return cjk + latin_words

    def sentences(self):
        text = self.text.replace("\n", " ")
        parts = re.split(r"[。！？!?\.]+", text)
        return [s.strip() for s in parts if s.strip()]

    def avg_sentence_words(self):
        sents = self.sentences()
        if not sents:
            return 0.0
        total = 0
        for s in sents:
            cjk = len(re.findall(r"[一-鿿]", s))
            latin = len(re.findall(r"[A-Za-z][A-Za-z'-]*", s))
            total += cjk + latin
        return total / len(sents)

    def external_links(self):
        out = []
        for lk in self.links:
            href = lk.get("href", "")
            if href.startswith("http://") or href.startswith("https://"):
                out.append(lk)
        return out

    def number_count(self):
        # 先剔除 ISO 日期和版本号,避免把 2025-06-22 / 1.2.3 当成统计数字
        text = re.sub(r"\d{4}-\d{2}-\d{2}", " ", self.text)
        text = re.sub(r"\bv?\d+\.\d+(?:\.\d+)+\b", " ", text)
        return len(re.findall(r"\d+(?:[.,]\d+)?%?", text))


def from_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return HtmlDoc(fh.read())


def from_string(html):
    return HtmlDoc(html)
