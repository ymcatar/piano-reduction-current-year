class AlignmentMethod(object):
    '''
    Base class for an alignment method.
    '''

    def __init__(self):
        # The *args and **kwargs that can be used to reconstruct this algorithm
        self.args = [], {}

    all_keys = ['align_type', 'align']
    key = 'align'
    features = []

    def run(self, input_score_obj, output_score_obj, extra=False):
        raise NotImplementedError()
