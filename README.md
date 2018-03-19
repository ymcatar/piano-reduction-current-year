# Piano Reduction 2017

## Setup

1.  (Recommended but not required) Use a virtualenv:

    ```sh
    python3 -m venv venv

    # Every time before working on the shell:
    source venv/bin/activate
    ```

2.  Install dependencies:

    ```sh
    pip3 install -r requirements.txt

    # To install dev dependencies:
    pip3 install -r requirements-dev.txt
    ```

3.  Run `python3 learning/test.py` for usage.

## Development

-   Linting:

    ```sh
    flake8
    ```

-   Unit testing:

    ```sh
    pytest
    ```

## Command line interface

To access to command line, use:

```sh
python3 -m learning <args...>

# For help
python3 -m learning --help
python3 -m learning <command> --help

# Train model only
# This defaults to saving the model to "trained/<model name>.model".
python3 -m learning.models.<model name> train

# Reduce from trained model
# This defaults to loading from the above file.
python3 -m learning.models.<model name> reduce [-o <output file>] <input file>[:<reduced file>]

python3 -m learning reduce -m <model file> [-o <output file>] <input file>[:<reduced file>]

# Inspect sample pair
python3 -m learning inspect <original file>:<reduced file>
```
