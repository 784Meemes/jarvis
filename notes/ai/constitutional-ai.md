# Constitutional AI

Constitutional AI (CAI) is Anthropic's approach to alignment: instead of
relying purely on human feedback to say what's good or bad, the model is
given a written "constitution" — a set of principles — and trained to
critique and revise its own responses against those principles.

This is one of the core techniques behind Claude, and it reduces (though
doesn't eliminate) the need for large volumes of human-labeled harmful vs.
harmless examples. It's a form of scalable oversight: using the model's own
Large Language Models capabilities to help supervise itself.
