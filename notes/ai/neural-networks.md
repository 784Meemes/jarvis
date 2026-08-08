# Neural Networks

A neural network is a stack of simple functions — weighted sums and
nonlinearities — arranged in layers and trained by Backpropagation to
minimize a loss function. Individually each unit is trivial; the expressive
power comes from composition and scale.

Large Language Models are just a particular architecture (the transformer)
built from this same substrate, trained on text instead of images or
tabular data. Understanding gradient descent and backpropagation is
foundational to understanding why LLMs behave the way they do, including
their failure modes.
