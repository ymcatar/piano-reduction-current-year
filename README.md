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

# Train model and reduce
python3 -m learning reduce [-o <output file>] <input file>

# Train model only
python3 -m learning train [-m <path.to.Model>] -o <output model file>

# Reduce from trained model (Supply the reduced file to evaluate test metrics)
python3 -m learning reduce -m <model file> [-o <output file>] <input file>[:<reduced file>]

# Inspect sample pair
python3 -m learning inspect <original file>:<reduced file>
```

## Feature caching

When working on machine learning models, it is desirable to train models
quickly. To remove the overhead of the various feature extraction Algorithms,
the flag `--cache` can be used to cache the extracted features in
`sample/cache`. However, the cache must be manually cleared when those
Algorithms are modified.
