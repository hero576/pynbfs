import collections
import datetime
import os
import re
import struct
import time
import traceback
from io import BytesIO

from lib.elements import *
from lib.attributes import *
from lib.constants import *

# Whether to preserve namespaces in element's names
from lib.utils import *
from lib.xml_parser import XMLParser

PRESERVE_NAMESPACES = False


class Decoder:
    def __init__(self):
        self.output = ''

    def parse(self,data,offse=0):
        self.index = 0
        start_envelope = data.find(b'\x56\x02\x0B')
        fp = BytesIO(data)
        if start_envelope:
            # In that case, should follow [MC-NBFSE] specs, i.e. uses StringTable (in-band dictionary)
            # In that case, packets are built as follow:
            # [size of in-band elements (7bit-int)][in-band elements][56 02 0B .... .NET Binary content]
            (size_marked, l) = Net7BitInteger.decode7bit(data)
            if size_marked + l != start_envelope:
                # If here it means that in-band elements are not prefixed by its size
                l = 0
            # Extraction of in-band elements
            inband_elements = self.extract_inband_elements(data[l:start_envelope])
        else:
            start_envelope = 0
        try:
            return self.binary_to_xml(fp,offse+start_envelope)
        except:
            # [MC-NBFS] if start_envelope == 0
            # [MC-NBFX] if start_envelope == -1 (pattern not found)
            raise Exception("Exception while parsing data near position ")

    def binary_to_xml(self, fp, offset):
        try:
            # Decoding
            fp.read(offset)
            self.records = Record.parse(fp)
            fp.close()
            output = ['']
            print_records(self.records, output=output, fp_enabled=False)
            self.output = output[0]
            return self.output
        except Exception as e:
            print(traceback.format_exc())
            # traceback.print_exc()
            return False

    def xml_to_mcnbfs(self, content):
        """
        Encode XML into .NET Binary in standard format [MC-NBFS]
        """
        try:
            r = XMLParser.parse(content)
            data = dump_records(r)
            self.output = data
            return data
        except Exception as e:
            raise Exception(traceback.format_exc())

    def xml_to_mcnbfse(self, content, nosizeprefix):
        """
        Encode XML into .NET Binary in format [MC-NBFSE]
        """

        # Extract in-band dictionary from xml and produce binary
        inband_dictionary = self.extract_inband_dictionary_from_xml()
        binary_inband = self.inband_dictionary_to_binary_format(inband_dictionary, nosizeprefix)
        # Convert XML to .NET Binary
        if not self.xml_to_mcnbfs(content):
            return False
        # Concatenate in-band dictionary + .NET Binary standard [MC-NBFS] => .NET Binary [MC-NBFSE]
        self.output = binary_inband + self.output
        return self.output

    def build_partial_stringtable(self, inband_elements):
        """
        Use extracted in-band elements to populate partial StringTable with correct index
        """
        # Find reference max index into decoded data
        max_index = 1
        regex = re.compile(r'\[\[VALUE_0x([0-9a-fA-F]+)\]\]')
        for match in regex.finditer(self.output):
            if int(match.group(1), 16) > max_index:
                max_index = int(match.group(1), 16)

        # Compute beginning index of partial StringTable
        begin_index = max_index - (len(inband_elements) - 1) * 2

        # Build partial StringTable
        partial_stringtable = collections.OrderedDict()
        for i in range(begin_index, max_index + 1, 2):
            partial_stringtable[i] = inband_elements.pop(0)
        return partial_stringtable

    def extract_inband_elements(self, data):
        """
        Extract in-band elements transmitted into the packet.
        Those elements are used to update the StringTable kept in memory at client and server sides.
        """
        i = 0
        elements = []
        print('data: ',data)
        while i < len(data):
            print('data ',i,data[i])
            next_len = data[i]
            # next_len = int(data[i].encode('hex'), 16)
            elements.append(data[i + 1:i + 1 + next_len])
            i = i + 1 + next_len

        return elements

    def replace_reference_stringtable(self, partial_stringtable):
        """
        Replace reference to elements in StringTable when it is known.
        Format : [[xxxx|ST_0xxx]]
        """
        for index in partial_stringtable.keys():
            self.output = self.output.replace('[[VALUE_0x%02x]]' % index,
                                              '[[%s|ST_0x%02x]]' % (partial_stringtable[index], index))
        return

    def emphasize_stringtable_elements(self, xml):
        """
        Put reference to StringTable elements into XML in strong
        """
        regex = re.compile(r'\[\[VALUE_0x(?P<number>[0-9A-Fa-f]+)\]\]')
        xml = re.sub(regex, Style.BRIGHT + '[[VALUE_0x\g<number>]]' + Style.RESET_ALL, xml)
        regex = re.compile(r'ST_0x(?P<number>[0-9A-Fa-f]+)\]\]')
        xml = re.sub(regex, Style.BRIGHT + 'ST_0x\g<number>' + Style.RESET_ALL + ']]', xml)
        return xml

    def extract_inband_dictionary_from_xml(self):
        """
        Extract known elements from StringTable that are inside the XML
        They must respect the syntax [[VALUE|ST_0xXX]]
        Those elements are aimed at being converted in binary
        """
        inband_dictionary = {}

        # Find all reference to in-band dictionary into xml
        regex = re.compile(r'\[\[(.*?)\|ST_0x([0-9a-fA-F]+)\]\]')
        for match in regex.finditer(self.input):
            inband_dictionary[int(match.group(2), 16)] = match.group(1)

        # Replace [[VALUE|ST_0xXX]] by [[VALUE_0xXX]] into xml
        regex = re.compile(r'\[\[(?P<value>.)*?\|ST_0x(?P<number>[0-9a-fA-F]+)\]\]')
        self.input = re.sub(regex, '[[VALUE_0x\g<number>]]', self.input)

        # print(self.input)
        return inband_dictionary

    def inband_dictionary_to_binary_format(self, inband_dictionary, nosizeprefix):
        """
        Convert in-band dictionary (previously extracted from XML) in binary format.
        Resulting binary data is aimed at being prefixed to .NET Binary data
        """
        length = 0
        for index in inband_dictionary.keys():
            length += 1 + len(inband_dictionary[index])

        binary = bytearray(length)
        i = 0
        list_index = inband_dictionary.keys()
        list_index.sort()
        for index in list_index:
            binary[i] = len(inband_dictionary[index])
            i += 1
            for c in inband_dictionary[index]:
                binary[i] = c
                i += 1

        # Prefix in-band dictionary with its size in 7-Bit Integer format,
        # unless nosizeprefix == True
        if not nosizeprefix:
            binary = Net7BitInteger.encode7bit(length) + binary

        return binary

parse = Decoder()


