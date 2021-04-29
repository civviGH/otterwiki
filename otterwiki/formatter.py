#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set et ts=8 sts=4 sw=4 ai:

import os
import re
import git

import mistune
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import html
from pygments.util import ClassNotFound

from flask import url_for
from otterwiki.storage import storage
from otterwiki.util import get_pagename, slugify

from pprint import pprint

# Please check https://github.com/lepture/mistune-contrib
# for mistune extensions.

#class MyPygmentsMixin(object):
class MyRenderer(mistune.Renderer):
    toc_count = 0
    toc_tree = []
    toc_anchors = {}

    def reset_toc(self):
        self.toc_count = 0
        self.toc_tree = []
        self.toc_anchors = {}

    def block_code(self, code, lang):
        if not lang:
            return '\n<pre><code>%s</code></pre>\n' % \
                mistune.escape(code.strip())
        try:
            lexer = get_lexer_by_name(lang, stripall=True)
        except ClassNotFound:
            return '\n<pre><code>%s\n%s</code></pre>\n' % \
                (mistune.escape(lang.strip()), mistune.escape(code.strip()))
        formatter = html.HtmlFormatter(classprefix=".highlight ")
        return highlight(code, lexer, formatter)

    def header(self, text, level, raw=None):
        #rv = '<h%d id="toc-%d"><a id="">%s</h%d>\n' % (
        #    level, self.toc_count, text, level
        #)
        anchor = slugify(text)
        try:
            self.toc_anchors[anchor]+=1
            print(anchor)
            anchor = "{}-{}".format(anchor,self.toc_anchors[anchor])
        except KeyError:
            print("new anchor:", anchor)
            self.toc_anchors[anchor]=0

        rv = '<h{level} id="toc-{count}"><a id="{anchor}" href="#{anchor}">{text}<span class="anchor">&nbsp;</span></a></h{level}>\n'.format(
            level = level, count = self.toc_count, text = text, anchor = anchor,
        )
        self.toc_tree.append((self.toc_count, text, level, raw))
        self.toc_count += 1
        return rv

    def get_toc(self):
        return {
            "count": self.toc_count,
            "tree": self.toc_tree,
            "anchors": self.toc_anchors
        }

#class MyRenderer(mistune.Renderer, MyPygmentsMixin):
#    def __init__(self, *args, **kwargs):
#        super(MyRenderer, self).__init__(*args, **kwargs)

class MyInlineLexer(mistune.InlineLexer):
    def __init__(self, *args, **kwargs):
        super(MyInlineLexer, self).__init__(*args, **kwargs)
        self.enable_wiki_link()

    def enable_wiki_link(self):
        self.rules.wiki_link = re.compile(
            r'\[\['                   # [[
            r'([^\]]+)'               # ...
            r'\]\]'                   # ]]
        )
        self.default_rules.insert(0, 'wiki_link')
        # inner regular expression
        self.wiki_link_iwlre = re.compile(
                r'([^\|]+)\|?(.*)'
                )

    def output_wiki_link(self, m):
        # initial style
        style = ''
        # parse for title and pagename
        title, pagename = self.wiki_link_iwlre.findall(m.group(1))[0]
        # fetch all existing pages
        pages = [get_pagename(x).lower() for x in storage.list_files() if x.endswith(".md")]
        # if the pagename is empty the title is the pagename
        if pagename == '': pagename = title
        # check if page exists
        if pagename.lower() not in pages:
            style = ' class="notfound"'
        # generate link
        url = url_for('view', pagename=pagename)
        link = '<a href="{}"{}>{}</a>'.format(url,style,title)
        return link

_renderer = MyRenderer()
_inline = MyInlineLexer(_renderer)
_markdown = mistune.Markdown(renderer=_renderer, inline=_inline)

def parse_toc(raw_toc):
    if raw_toc["count"] == 0:
        return ""
    print(raw_toc)
    toc = """<div class="content-toc"><ul class="toc_list">"""
    for entry in raw_toc['tree']:
        _, name, layer, _ = entry
        if layer > 2:
            continue
        anchor = slugify(name)
        toc = toc + f"<li><a href='#{anchor}'>{' ' * layer}{name}</a></li>\n"
    toc = toc + "</ul></div>"
    return toc

def render_markdown(text):
    _renderer.reset_toc()
    md = _markdown(text)
    return md, parse_toc(_renderer.get_toc())
