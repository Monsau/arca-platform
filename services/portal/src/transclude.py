"""Module UI transclusion — the portal composes module pages into ITS OWN
document. Iframes are forbidden by design: the user must see one Arca Suite
page, not a stitched set of frames.

How it works:
  1. The portal fetches the module's UI document server-side (GET <service>
     + ui_base) with the session's SSO token.
  2. The module markup (<head> styles + <body> content) is inlined into the
     portal shell template (module.html) — one document, one design system.
  3. A <base href="/m/<key>/<ui_base>"> makes every relative asset URL and
     relative fetch() from the module resolve through the authenticated
     /m/<key>/ proxy, exactly as before.
  4. Absolute in-page asset URLs emitted by a module are rewritten to the
     same proxy prefix so nothing leaks the /ui/ paths to the browser.

Trust boundary: modules are first-party Suite code served from the platform's
own cluster — inlining their markup/scripts is the same trust domain as the
portal proxying their API calls.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

from .config import Module

logger = logging.getLogger(__name__)

_ASSET_ATTR = re.compile(r'(?P<attr>\b(?:src|href))="(?P<url>(?!/)(?!https?:)(?!data:)(?!#)(?!mailto:)[^"]+)"')


class _DocumentSplit(HTMLParser):
    """Split an HTML document into head-assets and body-inner markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.head_parts: list[str] = []
        self.body_parts: list[str] = []
        self._in_head = False
        self._in_body = False
        self._capture_depth = 0
        self._capture_tag: str | None = None

    def _target(self) -> list[str] | None:
        if self._capture_tag is not None or self._in_head or self._in_body:
            return self.head_parts if self._in_head else self.body_parts
        return None

    def _emit(self, data: str) -> None:
        target = self._target()
        if target is not None:
            target.append(data)

    def handle_starttag(self, tag, attrs):
        attr_txt = "".join(
            f' {name}="{value}"' if value is not None else f" {name}"
            for name, value in attrs
        )
        raw = f"<{tag}{attr_txt}>"
        if tag == "head":
            self._in_head = True
            return
        if tag == "body":
            self._in_body = True
            return
        if tag == "title" and self._in_head:
            return  # the portal shell owns the document title
        if tag in ("style", "script"):
            self._capture_tag = tag
            self._capture_depth = 1
        self._emit(raw)

    def handle_startendtag(self, tag, attrs):
        if not self._in_head and not self._in_body:
            return
        attr_txt = "".join(
            f' {name}="{value}"' if value is not None else f" {name}"
            for name, value in attrs
        )
        self._emit(f"<{tag}{attr_txt}/>")

    def handle_endtag(self, tag):
        if tag == "head":
            self._in_head = False
            return
        if tag == "body":
            self._in_body = False
            return
        if tag == "title" and not self._in_body:
            return  # matched the dropped head <title>
        if self._capture_tag == tag:
            self._capture_depth -= 1
            if self._capture_depth <= 0:
                self._emit(f"</{tag}>")
                self._capture_tag = None
                return
        self._emit(f"</{tag}>")

    def handle_data(self, data):
        # Raw text is only meaningful inside <style>/<script> (head) or as
        # text content of body elements; whitespace between head tags is noise.
        if self._capture_tag is not None or self._in_body:
            self._emit(data)

    def handle_comment(self, data):
        if self._capture_tag is not None or self._in_body:
            self._emit(f"<!--{data}-->")

    def handle_entityref(self, name):
        self._emit(f"&{name};")

    def handle_charref(self, name):
        self._emit(f"&#{name};")


@dataclass
class TranscludedDocument:
    head: str  # <style>/<link> assets to place before the module markup
    markup: str  # module body content, inlined into the portal page


def _rewrite_assets(fragment: str, proxy_prefix: str) -> str:
    """Point relative src/href at the /m/<key>/ authenticated proxy."""

    def _sub(match: re.Match) -> str:
        return f'{match.group("attr")}="{proxy_prefix}{match.group("url")}"'

    return _ASSET_ATTR.sub(_sub, fragment)


async def fetch_module_document(client: httpx.AsyncClient, module: Module,
                                token: str, timeout: float = 15.0) -> TranscludedDocument | None:
    """Fetch and split a module UI document. None when the module is
    unreachable or does not serve HTML — the caller renders an honest error."""
    ui = module.ui_base if module.ui_base.endswith("/") else module.ui_base + "/"
    url = f"{module.service.rstrip('/')}{ui}"
    try:
        resp = await client.get(
            url,
            headers={"authorization": f"Bearer {token}"},
            timeout=timeout,
            follow_redirects=True,
        )
    except httpx.HTTPError as exc:
        logger.warning("transclude %s failed: %s", module.key, exc)
        return None
    if resp.status_code != 200 or "text/html" not in resp.headers.get("content-type", ""):
        logger.warning("transclude %s: upstream %s %s", module.key,
                       resp.status_code, resp.headers.get("content-type"))
        return None

    parser = _DocumentSplit()
    parser.feed(resp.text)
    proxy_prefix = f"/m/{module.key}{ui}"
    return TranscludedDocument(
        head=_rewrite_assets("".join(parser.head_parts), proxy_prefix),
        markup=_rewrite_assets("".join(parser.body_parts), proxy_prefix),
    )
