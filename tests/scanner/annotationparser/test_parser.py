# -*- Mode: Python -*-
# GObject-Introspection - a framework for introspecting GObject libraries
# Copyright (C) 2012 Dieter Verfaillie <dieterv@optionexplicit.be>
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


'''
test_parser.py

Tests ensuring the "parse tree" built by annotationparser.py
continues to function correctly.
'''


import difflib
import os
import subprocess
import unittest
import xml.etree.ElementTree as etree

from giscanner.annotationparser import AnnotationParser
from giscanner.ast import Namespace
from giscanner.message import MessageLogger


XML_NS = 'http://schemas.gnome.org/gobject-introspection/2013/test'
XML_SCHEMA = os.path.abspath(os.path.join(os.path.dirname(__file__), 'tests.xsd'))
XML_LINT = None


class ChunkedIO(object):
    def __init__(self):
        self.buffer = []

    def write(self, s):
        self.buffer.append(s)

    def getvalue(self):
        return self.buffer


def ns(x):
    return x.replace('{}', '{%s}' % (XML_NS, ))


def validate(tests_file):
    global XML_LINT

    try:
        cmd = ['xmllint', '--noout', '--nonet', '--schema', XML_SCHEMA, tests_file]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = p.communicate()
    except OSError:
        if XML_LINT is None:
            XML_LINT = False
            print('warning: xmllint not found, validation of test definition files will be skipped')
    else:
        if p.returncode != 0:
            raise SystemExit(stdout)


class TestCommentBlock(unittest.TestCase):
    @classmethod
    def __create_test__(cls, logger, testcase):
        def do_test(self):
            output = ChunkedIO()
            logger._output = output

            # Parse GTK-Doc comment block
            commentblock = testcase.find(ns('{}input')).text
            parsed_docblock = AnnotationParser().parse_comment_block((commentblock, 'test.c', 1))
            parsed_tree = self.parsed2tree(parsed_docblock).split('\n')
            emitted_messages = [w[w.find(':') + 1:].strip() for w in output.getvalue()]

            # Get expected parser output
            expected_docblock = testcase.find(ns('{}parser/{}docblock'))
            expected_tree = self.expected2tree(expected_docblock).split('\n')

            expected_messages = []
            for w in testcase.findall(ns('{}parser/{}messages/{}message')):
                expected_messages.append(w.text.strip())

            # Compare parsed with expected GtkDocCommentBlock
            msg = 'Parsed DocBlock object tree does not match expected output:\n\n'
            msg += '%s\n\n' % (commentblock, )

            diff = difflib.unified_diff(expected_tree, parsed_tree,
                                        'Expected DocBlock', 'Parsed DocBlock',
                                        n=max(len(expected_tree), len(parsed_tree)),
                                        lineterm='')
            for line in diff:
                msg += '%s\n' % (line, )

            self.assertTrue(parsed_tree == expected_tree, msg)

            # Compare emitted with expected messages
            msg = 'Emitted messages do not match expected messages:\n\n'
            msg += '%s\n\n' % (commentblock, )
            msg += self._diff_messages(expected_messages, emitted_messages)
            self.assertTrue(len(expected_messages) == len(emitted_messages), msg)

            for emitted_message, expected_message in zip(emitted_messages, expected_messages):
                msg = 'Emitted message does not match expected message:\n\n'
                msg += '%s\n\n' % (commentblock, )
                msg += self._diff_messages([expected_message], [emitted_message])
                self.assertTrue(expected_message == emitted_message, msg)

        return do_test

    def parsed2tree(self, docblock):
        parsed = ''

        if docblock is not None:
            parsed += '<docblock>\n'

            parsed += '  <identifier>\n'
            parsed += '    <name>%s</name>\n' % (docblock.name, )
            if docblock.options.values:
                parsed += '    <annotations>\n'
                for key, value in docblock.options.values:
                    parsed += '      <annotation>\n'
                    parsed += '        <name>%s</name>\n' % (key, )
                    if value is not None:
                        options = value.all()
                        parsed += '        <options>\n'
                        for option in options:
                            parsed += '          <option>\n'
                            parsed += '            <name>%s</name>\n' % (option, )
                            if options[option] is not None:
                                parsed += '            <value>%s</value>\n' % (options[option], )
                            parsed += '          </option>\n'
                        parsed += '        </options>\n'
                    parsed += '      </annotation>\n'
                parsed += '    </annotations>\n'
            parsed += '  </identifier>\n'

            if docblock.params:
                parsed += '  <parameters>\n'
                for param_name in docblock.params:
                    param = docblock.params.get(param_name)
                    parsed += '    <parameter>\n'
                    parsed += '      <name>%s</name>\n' % (param_name, )
                    if param.options.values:
                        parsed += '      <annotations>\n'
                        for key, value in param.options.values:
                            parsed += '        <annotation>\n'
                            parsed += '          <name>%s</name>\n' % (key, )
                            if value is not None:
                                options = value.all()
                                parsed += '          <options>\n'
                                for option in options:
                                    parsed += '            <option>\n'
                                    parsed += '              <name>%s</name>\n' % (option, )
                                    if options[option] is not None:
                                        parsed += '              <value>%s</value>\n' % (options[option], )
                                    parsed += '            </option>\n'
                                parsed += '          </options>\n'
                            parsed += '        </annotation>\n'
                        parsed += '      </annotations>\n'
                    if param.comment or param.value:
                        parsed += '      <description>%s</description>\n' % (param.comment or param.value, )
                    parsed += '    </parameter>\n'
                parsed += '  </parameters>\n'

            if docblock.comment or docblock.value:
                parsed += '  <description>%s</description>\n' % (docblock.comment or docblock.value, )

            if docblock.tags:
                parsed += '  <tags>\n'
                for tag_name in docblock.tags:
                    tag = docblock.tags.get(tag_name)
                    parsed += '    <tag>\n'
                    parsed += '      <name>%s</name>\n' % (tag_name, )
                    if tag.options.values:
                        parsed += '      <annotations>\n'
                        for key, value in tag.options.values:
                            parsed += '        <annotation>\n'
                            parsed += '          <name>%s</name>\n' % (key, )
                            if value is not None:
                                options = value.all()
                                parsed += '          <options>\n'
                                for option in options:
                                    parsed += '            <option>\n'
                                    parsed += '              <name>%s</name>\n' % (option, )
                                    if options[option] is not None:
                                        parsed += '              <value>%s</value>\n' % (options[option], )
                                    parsed += '            </option>\n'
                                parsed += '          </options>\n'
                            parsed += '        </annotation>\n'
                        parsed += '      </annotations>\n'
                    if tag.comment or tag.value:
                        parsed += '      <description>%s</description>\n' % (tag.comment or tag.value, )
                    parsed += '    </tag>\n'
                parsed += '  </tags>\n'

            parsed += '</docblock>'

        return parsed

    def expected2tree(self, docblock):
        # Note: this sucks, but we can't rely on etree.tostring() to generate useable output :(

        expected = ''

        if docblock is not None:
            expected += '<docblock>\n'

            if docblock.find(ns('{}identifier')) is not None:
                expected += '  <identifier>\n'
                expected += '    <name>%s</name>\n' % (docblock.find(ns('{}identifier/{}name')).text, )
                annotations = docblock.find(ns('{}identifier/{}annotations'))
                if annotations is not None:
                    expected += '    <annotations>\n'
                    for annotation in annotations.findall(ns('{}annotation')):
                        expected += '      <annotation>\n'
                        expected += '        <name>%s</name>\n' % (annotation.find(ns('{}name')).text, )
                        if annotation.find(ns('{}options')) is not None:
                            expected += '        <options>\n'
                            for option in annotation.findall(ns('{}options/{}option')):
                                expected += '          <option>\n'
                                expected += '            <name>%s</name>\n' % (option.find(ns('{}name')).text, )
                                if option.find('value') is not None:
                                    expected += '            <value>%s</value>\n' % (option.find(ns('{}value')).text, )
                                expected += '          </option>\n'
                            expected += '        </options>\n'
                        expected += '      </annotation>\n'
                    expected += '    </annotations>\n'
                expected += '  </identifier>\n'

            parameters = docblock.find(ns('{}parameters'))
            if parameters is not None:
                expected += '  <parameters>\n'
                for parameter in parameters.findall(ns('{}parameter')):
                    expected += '    <parameter>\n'
                    expected += '      <name>%s</name>\n' % (parameter.find(ns('{}name')).text, )
                    annotations = parameter.find(ns('{}annotations'))
                    if annotations is not None:
                        expected += '      <annotations>\n'
                        for annotation in parameter.findall(ns('{}annotations/{}annotation')):
                            expected += '        <annotation>\n'
                            expected += '          <name>%s</name>\n' % (annotation.find(ns('{}name')).text, )
                            if annotation.find(ns('{}options')) is not None:
                                expected += '          <options>\n'
                                for option in annotation.findall(ns('{}options/{}option')):
                                    expected += '            <option>\n'
                                    expected += '              <name>%s</name>\n' % (option.find(ns('{}name')).text, )
                                    if option.find(ns('{}value')) is not None:
                                        expected += '              <value>%s</value>\n' % (option.find(ns('{}value')).text, )
                                    expected += '            </option>\n'
                                expected += '          </options>\n'
                            expected += '        </annotation>\n'
                        expected += '      </annotations>\n'
                    if parameter.find(ns('{}description')) is not None:
                        expected += '      <description>%s</description>\n' % (parameter.find(ns('{}description')).text, )
                    expected += '    </parameter>\n'
                expected += '  </parameters>\n'

            description = docblock.find(ns('{}description'))
            if description is not None:
                expected += '  <description>%s</description>\n' % (description.text, )

            tags = docblock.find(ns('{}tags'))
            if tags is not None:
                expected += '  <tags>\n'
                for tag in tags.findall(ns('{}tag')):
                    expected += '    <tag>\n'
                    expected += '      <name>%s</name>\n' % (tag.find(ns('{}name')).text, )
                    annotations = tag.find(ns('{}annotations'))
                    if annotations is not None:
                        expected += '      <annotations>\n'
                        for annotation in tag.findall(ns('{}annotations/{}annotation')):
                            expected += '        <annotation>\n'
                            expected += '          <name>%s</name>\n' % (annotation.find(ns('{}name')).text, )
                            if annotation.find(ns('{}options')) is not None:
                                expected += '          <options>\n'
                                for option in annotation.findall(ns('{}options/{}option')):
                                    expected += '            <option>\n'
                                    expected += '              <name>%s</name>\n' % (option.find(ns('{}name')).text, )
                                    if option.find(ns('{}value')) is not None:
                                        expected += '              <value>%s</value>\n' % (option.find(ns('{}value')).text, )
                                    expected += '            </option>\n'
                                expected += '          </options>\n'
                            expected += '        </annotation>\n'
                        expected += '      </annotations>\n'
                    if tag.find(ns('{}description')) is not None:
                        expected += '      <description>%s</description>\n' % (tag.find(ns('{}description')).text, )
                    expected += '    </tag>\n'
                expected += '  </tags>\n'

            expected += '</docblock>'

        return expected

    def _diff_messages(self, a, b):
        retval = ''
        started = False

        for group in difflib.SequenceMatcher(None, a, b).get_grouped_opcodes(3):
            if not started:
                started = True
                retval += '--- expected\n'
                retval += '+++ emitted\n'

            for tag, i1, i2, j1, j2 in group:
                if tag == 'equal':
                    for line in a[i1:i2]:
                        for l in line.split('\n'):
                            retval += ' ' + l + '\n'
                    continue

                if tag in ('replace', 'delete'):
                    for line in a[i1:i2]:
                        for l in line.split('\n'):
                            retval += '-' + l + '\n'

                if tag in ('replace', 'insert'):
                    for line in b[j1:j2]:
                        for l in line.split('\n'):
                            retval += '+' + l + '\n'

        return retval


def create_tests(logger, tests_dir, tests_file):
    tests_name = os.path.relpath(tests_file[:-4], tests_dir).replace('/', '.').replace('\\', '.')
    tests_tree = etree.parse(tests_file).getroot()

    fix_cdata_elements = tests_tree.findall(ns('{}test/{}input'))
    fix_cdata_elements += tests_tree.findall(ns('.//{}description'))

    for element in fix_cdata_elements:
        if element.text:
            element.text = element.text.replace('{{?', '<!')
            element.text = element.text.replace('}}', '>')

    for counter, test in enumerate(tests_tree.findall(ns('{}test'))):
        test_name = 'test_%s.%03d' % (tests_name, counter + 1)
        test_method = TestCommentBlock.__create_test__(logger, test)
        setattr(TestCommentBlock, test_name, test_method)


if __name__ == '__main__':
    # Initialize message logger
    namespace = Namespace('Test', '1.0')
    logger = MessageLogger.get(namespace=namespace)
    logger.enable_warnings(True)

    # Load test cases from disc
    tests_dir = os.path.dirname(os.path.abspath(__file__))

    for dirpath, dirnames, filenames in os.walk(tests_dir):
        for filename in filenames:
            tests_file = os.path.join(dirpath, filename)
            if os.path.basename(tests_file).endswith('.xml'):
                validate(tests_file)
                create_tests(logger, tests_dir, tests_file)

    # Run test suite
    unittest.main()
