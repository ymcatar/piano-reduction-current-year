import numpy as np

from expiringdict import ExpiringDict

from util import split_to_hands, get_note_dist

cache = ExpiringDict(max_len=1000, max_age_seconds=100)


def cost_model(prev, curr, next, max_hand_span=7, frame_length=1.0):

    cache_key = str(prev) + '@' + str(curr) + '@' + str(next)

    if cache_key in cache:
        return cache[cache_key]

    prev = [n for n in prev if not n.deleted and n.hand and n.finger]
    curr = [n for n in curr if not n.deleted and n.hand and n.finger]
    next = [n for n in next if not n.deleted and n.hand and n.finger]

    # higher penalty for number of notes
    # left_hand_notes, right_hand_notes = split_to_hands(curr, max_hand_span)
    # note_count_cost = len(left_hand_notes) * 5 + len(right_hand_notes) * 5
    note_count_cost = len(curr) * 2

    # higher penalty for previous and next frame are both busy
    busy_cost = (len(prev) + len(next)) * 2

    # record where the fingers are
    prev_fingers, curr_fingers = {}, {}

    for n in prev:
        finger = n.finger if n.hand == 'L' else n.finger + 5
        prev_fingers[finger] = n

    for n in curr:
        finger = n.finger if n.hand == 'L' else n.finger + 5
        curr_fingers[finger] = n

    # record finger position change
    total_movement = 0
    total_new_placement = 0

    for finger in range(1, 11):

        # current finger are in both prev & curr frame => movement cost
        if finger in prev_fingers and finger in curr_fingers:
            prev_ps = prev_fingers[finger].note.pitch.ps
            curr_ps = curr_fingers[finger].note.pitch.ps
            total_movement += get_note_dist(curr_ps, prev_ps)

        # current finger are only in current frame => new placement cost
        if finger not in prev_fingers and finger in curr_fingers:

            search_range = range(1, 6) \
                if finger in range(1, 6) else range(6, 11)

            prev = [
                n.note.pitch.ps for key, n in prev_fingers.items()
                if key in search_range
            ]

            curr_ps = curr_fingers[finger].note.pitch.ps

            if len(prev) != 0:
                total_new_placement += get_note_dist(curr_ps, np.median(prev))

    total_cost = note_count_cost + busy_cost + total_movement + total_new_placement
    total_cost = total_cost / (frame_length + 1.0)  # normalize total_cost by frame_length

    cache[cache_key] = total_cost
    return total_cost


def get_cost_array(notes):
    costs = []
    for triplet in zip(notes, notes[1:], notes[2:]):
        prev_item, curr_item, next_item = triplet
        _, prev_frame = prev_item
        curr_offset, curr_frame = curr_item
        next_offset, next_frame = next_item
        cost = cost_model(prev_frame, curr_frame, next_frame,
                          frame_length=(next_offset-curr_offset))
        costs.append(cost)
    return costs


def get_total_cost(notes):

    costs = get_cost_array(notes)
    return sum(costs, 0)


def get_windowed_cost(measures, index, window_size=3):

    lower = max(0, index - 2)
    upper = min(index + 2, len(measures))

    window = measures[lower:upper]
    return get_total_cost(window)
