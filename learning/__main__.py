if __name__ == '__main__':
    from .models import nn as default_model
    from .cli import run_model_cli

    run_model_cli(default_model)
