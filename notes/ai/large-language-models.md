# Large Language Models

Large Language Models (LLMs) are neural networks trained on enormous text
corpora to predict the next token in a sequence. Scale — parameters, data,
and compute — turns out to be the dominant driver of capability, a pattern
often called the scaling laws.

Modern assistants like Claude are built on this architecture, fine-tuned
with techniques such as [[Constitutional AI]] to make them more helpful and
harmless. Getting good behavior out of an LLM without retraining it is the
whole discipline of Prompt Engineering — phrasing, examples, and structure
all change what the model produces.

Under the hood, everything traces back to Neural Networks and the
transformer's attention mechanism, which lets the model weigh every token
against every other token in its context window.
