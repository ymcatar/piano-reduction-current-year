class AlignmentMethod(object):
    '''
    Base class for an alignment method.
    '''

    def __init__(self):
        pass

    all_keys = ['align_type', 'align']
    key = 'align'
    features = []

    @property
    def args(self):
        '''
        Returns the *args and **kwargs that can be used to reconstruct this
        algorithm.
        '''
        return ([], {})

    def run(self, input_score_obj, output_score_obj, extra=False):
        raise NotImplementedError()
