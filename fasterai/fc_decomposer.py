import torch
import torch.nn as nn
import torch.nn.functional as F
import copy


class FCDecomposer:

    def __init__(self):
        super().__init__()
        
    def decompose(self, model, percent_removed=0.5):

        new_model = copy.deepcopy(model)

        module_names = list(new_model._modules)

        for k, name in enumerate(module_names):

            if len(list(new_model._modules[name]._modules)) > 0:
                new_model._modules[name] = self.decompose(new_model._modules[name], percent_removed)

            else:
                if isinstance(new_model._modules[name], nn.Linear):
                    # Folded BN
                    layer = self.SVD(new_model._modules[name], percent_removed)

                    # Replace old weight values
                    new_model._modules[name] = layer # Replace the FC Layer by the decomposed version
        return new_model


    def SVD(self, layer, percent_removed):

        W = layer.weight.data
        U, S, V = torch.svd(W)
        L = int((1.-percent_removed)*U.shape[0])
        W1 = U[:,:L]
        W2 = torch.diag(S[:L]) @ V[:,:L].t()
        layer_1 = nn.Linear(in_features=layer.in_features, 
                    out_features=L, bias=False)
        layer_1.weight.data = W2

        layer_2 = nn.Linear(in_features=L, 
                    out_features=layer.out_features, bias=True)
        layer_2.weight.data = W1

        if layer.bias.data is None: 
            layer_2.bias.data = torch.zeros(*layer.out_features.shape)
        else:
            layer_2.bias.data = layer.bias.data

        return nn.Sequential(layer_1, layer_2)