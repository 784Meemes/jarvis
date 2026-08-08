# Backpropagation

Backpropagation is the algorithm that makes training Neural Networks
tractable: it computes the gradient of the loss with respect to every
weight in the network by applying the chain rule backward through the
computation graph, layer by layer.

Without an efficient way to compute these gradients, models with billions
of parameters — like today's Large Language Models — would be impossible
to train. It's easy to take for granted, but backprop is the quiet engine
behind almost all of modern deep learning.
