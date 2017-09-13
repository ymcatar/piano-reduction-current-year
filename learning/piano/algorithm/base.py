class ReductionAlgorithm(object):
    '''
    Base class of all parameters, each contains a list of labels to allow multiple markings by one parameter
    '''

    _type = 'unknown'

    @property
    def type(self):
        return _type

    @property
    def allKeys(self):
        return [self.key]

    @property
    def key(self):
        return str(self._key) + '_' + str(self.__class__._type)

    @key.setter
    def key(self, key):
        self._key = key

    @property
    def parts(self):
        return self._parts

    def __init__(self, parts=[]):
        super(ReductionAlgorithm, self).__init__()
        self._key = '!'
        self._parts = parts

    def createMarkingsOn(self, score):
        pass
