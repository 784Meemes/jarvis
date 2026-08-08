# Prompt Engineering

Prompt Engineering is the practice of shaping the input to a Large Language
Model so it produces the output you actually want, without changing the
model's weights. It covers instructions, examples (few-shot prompting),
formatting, and system messages.

One especially useful technique is [[Chain of Thought]] prompting, where
you ask the model to reason step by step before giving a final answer.
This tends to improve performance on tasks that require multi-step logic,
arithmetic, or planning — essentially giving the model more "scratch space"
to think in before it commits to an answer.

Claude responds particularly well to clear, structured prompts with explicit
success criteria.
