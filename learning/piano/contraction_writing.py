import copy
from .alignment import align_all_notes
from .contraction import IndexMapping
from .score import ScoreObject
from postprocessor.multipart_reducer import MultipartReducer, LEFT_HAND, RIGHT_HAND


def create_contracted_score_obj(entry, structure_data):
    '''
    Given a PreProcessedEntry, construct a contracted input score object with
    the contracted annotations.
    '''

    obj_copy = ScoreObject(copy.deepcopy(entry.input.score))
    for n in obj_copy.notes:
        if entry.mapping.is_contracted(obj_copy.index(n)):
            n.editorial.misc['hand'] = None
        else:
            n.editorial.misc['hand'] = RIGHT_HAND if n.pitch.ps >= 60 else LEFT_HAND

    contracted = MultipartReducer(obj_copy.score).reduce()
    contracted_obj = ScoreObject(contracted)
    contracted = contracted_obj.score

    # Attach markings
    def key_func(n, offset, precision):
        return (int(offset * precision), n.pitch.ps)
    alignment = align_all_notes(contracted, entry.input.score, ignore_parts=True, key_func=key_func)

    inotes = list(entry.input.notes)
    cnotes = list(contracted_obj.notes)
    mapping = [None] * len(entry.features)  # From contracted input index to contracted score index
    for cidx, n in enumerate(contracted_obj.notes):
        for m in alignment[n]:  # We hope the alignment is one-to-one
            iidx = entry.mapping[entry.input.index(m)]
            cnotes[cidx].editorial.misc.update(inotes[iidx].editorial.misc)
            mapping[iidx] = cidx

    mapping = IndexMapping(mapping, output_size=len(contracted_obj), aggregator=lambda i: i[0])
    structure_data = {k: list(mapping.map_structure(entry.mapping.map_structure(dict(v))).items())
                      for k, v in entry.structures.items()}

    return contracted_obj, structure_data
