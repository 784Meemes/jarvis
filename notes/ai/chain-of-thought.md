# Chain of Thought

Chain of thought is a Prompt Engineering technique where a Large Language
Model is encouraged — either by instruction or by example — to write out
its intermediate reasoning steps before producing a final answer.

It matters because next-token prediction is inherently sequential: a model
that jumps straight to an answer has to compute the whole thing in a single
forward pass, while a model that reasons aloud can use its own prior output
as additional context. In practice this substantially improves accuracy on
math, logic, and multi-hop reasoning tasks.
