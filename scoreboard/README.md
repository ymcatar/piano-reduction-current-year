# Scoreboard

> Colouring musical scores

## Usage

Make sure MuseScore is installed.

```sh
# Before the first run
(cd scoreboard && yarn && yarn run build)

# Run the server
python3 -m scoreboard.server
```

How it works: Your code can invoke the LogWriter API (in `scoreboard.writer`) to
output feature definition and serialized scores. For example:

```python
import scoreboard.writer as writerlib
from learning.algorithm.base import iter_notes

for n in iter_notes(score, recurse=True):
    n.editorial.misc['is_note_c'] = n.pitch.name == 'C'

writer = writerlib.LogWriter('log')
writer.add_feature(
    writerlib.BoolFeature('is_note_c', help='Whether the note has pitch C'))
writer.add_score('input', score)
writer.finalize()
```

## Build Setup

``` bash
# install dependencies
yarn

# serve with hot reload at localhost:8080
yarn run dev

# build for production with minification
yarn run build
```

For detailed explanation on how things work, consult the [docs for vue-loader](http://vuejs.github.io/vue-loader).
