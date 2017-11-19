import tflearn
from .base import BaseModel


class TflearnModel(tflearn.DNN, BaseModel):
    def __init__(self, reducer, net, *args, **kwargs):
        self.reducer = reducer

        tflearn.DNN.__init__(self, net, *args, **kwargs)
