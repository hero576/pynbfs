from lib.decoder import parse

class NBFS:
    def __init__(self):
        pass

    def bin2xml(self, data):
        '''
        .NET Binary to XML
        :param bytes:
        :return:
        '''
        assert isinstance(data, bytes), 'Input data should be byte type.'
        return parse.parse(data)

    def xml2bin(self, content):
        '''
        Same as xml2mcnbfs
        :param content:
        :return:
        '''
        return self.xml2mcnbfs(content)

    def xml2mcnbfs(self, content):
        '''
        XML to .NET Binary in format [MC-NBFS] (standard)
        :param content:
        :return:
        '''
        return parse.xml_to_mcnbfs(content)

    def xml2mcnbfse(self, content,nosizeprefix):
        '''
        XML to .NET Binary in format [MC-NBFSE] with in-band dictionary
        :param content:
        :return:
        '''
        return parse.xml_to_mcnbfse(content,nosizeprefix)
