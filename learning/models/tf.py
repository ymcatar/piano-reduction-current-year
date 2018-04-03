import tflearn
from .base import BaseModel


class TflearnModel(tflearn.DNN, BaseModel):
    def __init__(self, pre_processor, net, *args, **kwargs):
        self.pre_processor = pre_processor

        tflearn.DNN.__init__(self, net, *args, **kwargs)
