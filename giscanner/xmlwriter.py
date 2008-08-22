# -*- Mode: Python -*-
# GObject-Introspection - a framework for introspecting GObject libraries
# Copyright (C) 2008  Johan Dahlin
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

from contextlib import contextmanager
from cStringIO import StringIO
from xml.sax.saxutils import quoteattr


class XMLWriter(object):

    def __init__(self):
        self._data = StringIO()
        self._data.write('<?xml version="1.0"?>\n')
        self._tag_stack = []
        self._indent = 0
        self._indent_unit = 2
        self._indent_char = ' '

    # Private

    def _calc_attrs_length(self, attributes, indent):
        if indent == -1:
            return -1
        attr_length = 0
        for attr, value in attributes:
            if value is None:
                raise ValueError(
                    "value for attribute %r cannot be None" % (attr, ))
            attr_length += 2 + len(attr) + len(quoteattr(value))
        return attr_length + indent + self._indent

    def _collect_attributes(self, tag_name, attributes, indent=-1):
        if not attributes:
            return ''
        if self._calc_attrs_length(attributes, indent) > 79:
            indent_len = self._indent + len(tag_name) + 1
        else:
            indent_len = 0
        first = True
        attr_value = ''
        for attr, value in attributes:
            if indent_len and not first:
                attr_value += '\n%s' % (self._indent_char * indent_len)
            if value is None:
                raise ValueError(
                    "value for attribute %r cannot be None" % (attr, ))
            attr_value += ' %s=%s' % (attr, quoteattr(value))
            if first:
                first = False
        return attr_value

    def _open_tag(self, tag_name, attributes=None):
        attrs = self._collect_attributes(
            tag_name, attributes, len(tag_name) + 2)
        self.write_line('<%s%s>' % (tag_name, attrs))

    def _close_tag(self, tag_name):
        self.write_line('</%s>' % (tag_name, ))

    # Public API

    def get_xml(self):
        return self._data.getvalue()

    def write_line(self, line=''):
        self._data.write('%s%s\n' % (self._indent_char * self._indent, line))

    def write_tag(self, tag_name, attributes, data=None):
        if attributes is None:
            attributes = []
        prefix = '<%s' % (tag_name, )
        if data is not None:
            suffix = '>%s</%s>' % (data, tag_name)
        else:
            suffix = '/>'
        attrs = self._collect_attributes(
            tag_name, attributes, len(prefix) + len(suffix))
        self.write_line(prefix + attrs + suffix)

    def push_tag(self, tag_name, attributes=None):
        self._open_tag(tag_name, attributes)
        self._tag_stack.append(tag_name)
        self._indent += self._indent_unit

    def pop_tag(self):
        self._indent -= self._indent_unit
        tag_name = self._tag_stack.pop()
        self._close_tag(tag_name)
        return tag_name

    @contextmanager
    def tagcontext(self, tag_name, attributes=None):
        self.push_tag(tag_name, attributes)
        try:
            yield
        finally:
            self.pop_tag()


def test():
    w = XMLWriter()
    w.push_tag('repository')
    w.push_tag('namespace')
    w.push_tag('enumeration')
    w.push_tag('member',
               [('name', 'west'),
                ('value', '7'),
                ('c:identifier', 'GTK_ANCHOR_WEST'),
                ('glib:nick', 'west')])

    w.pop_tag()
    w.pop_tag()
    w.pop_tag()
    x = w.get_xml()
    lines = x.split('\n')
    import pprint
    pprint.pprint(lines)
    assert len(lines[3]) < 80, len(lines[3])

if __name__ == '__main__':
    test()
