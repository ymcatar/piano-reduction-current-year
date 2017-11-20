most = > 50%


def most_has_overlap(first, second):
    first_intervals = [Interval(*i) for i in first]
    second_intervals = [Interval(*i) for i in second]

    count = 0
    tree = IntervalTree(first_intervals)
    for interval in second_intervals:
        if tree.search(*interval):
            count += 1
    if count / (len(second_intervals) * 2) > 0.5:
        return True

    count = 0
    tree = IntervalTree(second_intervals)
    for interval in first_intervals:
        if tree.search(*interval):
            count += 1
    if count / (len(first_intervals) * 2) > 0.5:
        return True

    return False
