window.GRAPH = {
  "nodes": [
    {
      "id": 0,
      "label": "Backpropagation",
      "group": "ai",
      "excerpt": "Backpropagation is the algorithm that makes training Neural Networks tractable: it computes the gradient of the loss with respect to every weight in the network by applying the chain rule backward through the computation graph, layer by layer. Without an efficient way to compute these gradients, models with billions of parameters \u2014 like today's Large Language Models \u2014 would be impossible to train. It's easy to take for granted, but backprop is the quiet engine behind almost all of modern deep learning.",
      "path": "notes/ai/backpropagation.md"
    },
    {
      "id": 1,
      "label": "Chain of Thought",
      "group": "ai",
      "excerpt": "Chain of thought is a Prompt Engineering technique where a Large Language Model is encouraged \u2014 either by instruction or by example \u2014 to write out its intermediate reasoning steps before producing a final answer. It matters because next-token prediction is inherently sequential: a model that jumps straight to an answer has to compute the whole thing in a single forward pass, while a model that reasons aloud can use its own prior output as additional context. In practice this substantially improves accuracy on math, logic, and multi-hop reasoning tasks.",
      "path": "notes/ai/chain-of-thought.md"
    },
    {
      "id": 2,
      "label": "Claude",
      "group": "ai",
      "excerpt": "Claude is the family of large language models built by Anthropic. Claude is trained using Constitutional AI, a technique where the model critiques and revises its own outputs against a set of written principles rather than relying solely on human-labeled preference data. Claude powers the Jarvis Assistant project in this notebook, and is the model most of these notes were drafted and organized with. Its behavior is heavily shaped by Prompt Engineering choices at the system-prompt level \u2014 tone, caution, verbosity, and tool use all get tuned there.",
      "path": "notes/ai/claude.md"
    },
    {
      "id": 3,
      "label": "Constitutional AI",
      "group": "ai",
      "excerpt": "Constitutional AI (CAI) is Anthropic's approach to alignment: instead of relying purely on human feedback to say what's good or bad, the model is given a written \"constitution\" \u2014 a set of principles \u2014 and trained to critique and revise its own responses against those principles. This is one of the core techniques behind Claude, and it reduces (though doesn't eliminate) the need for large volumes of human-labeled harmful vs. harmless examples. It's a form of scalable oversight: using the model's own Large Language Models capabilities to help supervise itself.",
      "path": "notes/ai/constitutional-ai.md"
    },
    {
      "id": 4,
      "label": "Large Language Models",
      "group": "ai",
      "excerpt": "Large Language Models (LLMs) are neural networks trained on enormous text corpora to predict the next token in a sequence. Scale \u2014 parameters, data, and compute \u2014 turns out to be the dominant driver of capability, a pattern often called the scaling laws. Modern assistants like Claude are built on this architecture, fine-tuned with techniques such as Constitutional AI to make them more helpful and harmless. Getting good behavior out of an LLM without retraining it is the whole discipline of Prompt Engineering \u2014 phrasing, examples, and structure all change what the model produces. Under the hood, everything traces back to Neural Networks and the transformer's attention mechanism, which lets th\u2026",
      "path": "notes/ai/large-language-models.md"
    },
    {
      "id": 5,
      "label": "Neural Networks",
      "group": "ai",
      "excerpt": "A neural network is a stack of simple functions \u2014 weighted sums and nonlinearities \u2014 arranged in layers and trained by Backpropagation to minimize a loss function. Individually each unit is trivial; the expressive power comes from composition and scale. Large Language Models are just a particular architecture (the transformer) built from this same substrate, trained on text instead of images or tabular data. Understanding gradient descent and backpropagation is foundational to understanding why LLMs behave the way they do, including their failure modes.",
      "path": "notes/ai/neural-networks.md"
    },
    {
      "id": 6,
      "label": "Prompt Engineering",
      "group": "ai",
      "excerpt": "Prompt Engineering is the practice of shaping the input to a Large Language Model so it produces the output you actually want, without changing the model's weights. It covers instructions, examples (few-shot prompting), formatting, and system messages. One especially useful technique is Chain of Thought prompting, where you ask the model to reason step by step before giving a final answer. This tends to improve performance on tasks that require multi-step logic, arithmetic, or planning \u2014 essentially giving the model more \"scratch space\" to think in before it commits to an answer. Claude responds particularly well to clear, structured prompts with explicit success criteria.",
      "path": "notes/ai/prompt-engineering.md"
    },
    {
      "id": 7,
      "label": "Determinism",
      "group": "philosophy",
      "excerpt": "Determinism holds that the state of the universe at one time, together with the laws of nature, fixes the state of the universe at every later time \u2014 no genuine branching, no randomness that matters at the macro scale. Applied to human behavior, it implies every decision was, in principle, predictable in advance. This is the main foil in the Free Will debate. Interestingly, most Stoicism practitioners were also determinists in the physical sense (they believed in a rationally ordered, fated cosmos) while still insisting our judgments and reactions were meaningfully \"up to us\" \u2014 a position modern compatibilists would recognize.",
      "path": "notes/philosophy/determinism.md"
    },
    {
      "id": 8,
      "label": "Epictetus",
      "group": "philosophy",
      "excerpt": "Epictetus was born a slave, later freed, and became one of the most influential teachers of Stoicism. His core idea, distilled in the Enchiridion, is the \"dichotomy of control\": some things are up to us (opinion, desire, aversion) and some things are not (body, property, reputation) \u2014 peace of mind comes from investing your energy only in the former. This idea shows up, largely unattributed, throughout centuries of later self-help writing. Marcus Aurelius studied Epictetus's teachings closely, and Meditations quotes him directly in several places.",
      "path": "notes/philosophy/epictetus.md"
    },
    {
      "id": 9,
      "label": "Free Will",
      "group": "philosophy",
      "excerpt": "The free will debate asks whether our choices are genuinely \"up to us\" or are the inevitable output of prior causes \u2014 physical, psychological, or otherwise. Determinism is the thesis that every event, including human decisions, follows necessarily from what came before. Compatibilists argue free will and determinism aren't actually in conflict, as long as \"free\" is defined as acting according to your own reasons rather than as an ability to have done otherwise in an identical universe. This is close to the practical stance taken by Stoicism, which treats our judgments as the one thing genuinely within our control regardless of how the rest of the universe unfolds.",
      "path": "notes/philosophy/free-will.md"
    },
    {
      "id": 10,
      "label": "Marcus Aurelius",
      "group": "philosophy",
      "excerpt": "Marcus Aurelius was Roman emperor from 161 to 180 AD and one of the last of the \"Five Good Emperors.\" He is best known today not for his reign but for Meditations, a private journal of Stoicism-flavored reflections he never intended to publish. The book reads less like philosophy-as-argument and more like philosophy- as-practice: reminders to himself to stay disciplined, patient, and unbothered by things outside his control. It's a useful counterpoint to Epictetus, whose surviving work is lecture notes taken by a student rather than a private diary.",
      "path": "notes/philosophy/marcus-aurelius.md"
    },
    {
      "id": 11,
      "label": "Stoicism",
      "group": "philosophy",
      "excerpt": "Stoicism is a school of Hellenistic philosophy founded in Athens that teaches virtue, reason, and living in accordance with nature as the path to a good life. It draws a sharp line between what is \"up to us\" (our judgments, desires, and actions) and what is not (everything else). Its most famous Roman practitioner was Marcus Aurelius, whose private journal \u2014 later published as Meditations \u2014 is still one of the most widely read texts in the tradition. Another major voice is Epictetus, a former slave whose teachings emphasize discipline over one's own reactions rather than control over external events. Stoicism has an uneasy but interesting relationship with Free Will, since its ethics assume\u2026",
      "path": "notes/philosophy/stoicism.md"
    },
    {
      "id": 12,
      "label": "Home Automation",
      "group": "projects",
      "excerpt": "A longer-term idea for Jarvis Assistant: extend it past notes and chat into actually controlling things \u2014 lights, thermostat, locks \u2014 through a local hub rather than routing everything through a cloud vendor. Latency and privacy both favor keeping the control loop local, with the assistant layer sitting on top for natural-language commands. Nothing here is built yet; this note exists mostly as a placeholder and a reminder that the assistant's usefulness should eventually extend beyond answering questions and organizing notes like this Knowledge Galaxy.",
      "path": "notes/projects/home-automation.md"
    },
    {
      "id": 13,
      "label": "Jarvis Assistant",
      "group": "projects",
      "excerpt": "Jarvis Assistant is the umbrella project for this repository: a personal assistant built on top of Claude, with a growing set of tools bolted on around it \u2014 including this Knowledge Galaxy, a 3D visualization of every Markdown note in the vault. The idea is that notes shouldn't just sit in a folder; they should be explorable as a living map, with related ideas pulled physically closer together. Large Language Models are what make this practical: not just for running the assistant itself, but for tasks like Prompt Engineering the summarization step that generates each note's excerpt.",
      "path": "notes/projects/jarvis-assistant.md"
    },
    {
      "id": 14,
      "label": "Knowledge Galaxy",
      "group": "projects",
      "excerpt": "The Knowledge Galaxy is an interactive 3D graph of this entire notes vault: every Markdown file becomes a glowing node, colored by its folder, and linked to every other note it mentions or wikilinks to. Built with 3D Force Graph running entirely in the browser off a CDN \u2014 no build step. A small Python script (build.py) does the heavy lifting: it walks the vault, extracts a title and excerpt from each file, and figures out the edges by matching titles and wikilinks against every other note. The result is graph-data.js, a static file the viewer loads directly. It's part of the Jarvis Assistant project, and a proof that Git plus plain Markdown is enough of a database to build something visually\u2026",
      "path": "notes/projects/knowledge-galaxy.md"
    },
    {
      "id": 15,
      "label": "Git",
      "group": "tools",
      "excerpt": "Git is a distributed version control system: every clone is a full copy of the project's history, and commits are content-addressed snapshots linked into a graph rather than a simple linear diff chain. Branching and merging are cheap, which is what enables the whole pull-request workflow. GitHub is the most popular hosting service built on top of Git, adding code review, issue tracking, and CI on top of the underlying protocol. This notes vault itself lives in a Git repository, versioned right alongside the script that turns it into a graph.",
      "path": "notes/tools/git.md"
    },
    {
      "id": 16,
      "label": "GitHub",
      "group": "tools",
      "excerpt": "GitHub is a hosting platform for Git repositories that adds collaboration features on top: pull requests, code review, issues, and CI/CD via Actions. It's become the default place open-source (and a lot of private) code lives. The Jarvis Assistant project \u2014 including this knowledge galaxy \u2014 is developed and pushed to GitHub, with all history tracked through Git. Most day-to-day interaction with a repository, for a lot of developers now, happens through GitHub's web UI and API rather than the raw git CLI.",
      "path": "notes/tools/github.md"
    },
    {
      "id": 17,
      "label": "Markdown",
      "group": "tools",
      "excerpt": "Markdown is a lightweight plain-text formatting syntax created by John Gruber: headings with , emphasis with or , links, lists, and code blocks, all readable even unrendered. Its simplicity is exactly why it won as the default format for notes, READMEs, and documentation. Every note in this vault, including this one, is a plain .md file \u2014 which is what makes it possible for a small Python script to parse the whole collection into a graph without needing a database or a proprietary export format. Obsidian, GitHub, and countless other tools all read and render it natively.",
      "path": "notes/tools/markdown.md"
    },
    {
      "id": 18,
      "label": "Obsidian",
      "group": "tools",
      "excerpt": "Obsidian is a local-first note-taking app built around a folder of plain Markdown files and a graph view that visualizes links between them. Notes live on disk as ordinary .md files, which makes the vault portable and easy to script against \u2014 this whole knowledge galaxy project is essentially a from-scratch reimplementation of Obsidian's graph view in the browser. Obsidian popularized the Zettelkasten workflow for a mainstream audience: small, atomic notes connected by explicit links rather than buried in a folder hierarchy. Because everything is Markdown, notes stay readable and toolable outside the app itself.",
      "path": "notes/tools/obsidian.md"
    },
    {
      "id": 19,
      "label": "Zettelkasten",
      "group": "tools",
      "excerpt": "The Zettelkasten (\"slip box\") method is a note-taking system built around small, single-idea notes that are densely cross-linked rather than filed into a rigid hierarchy. It was popularized by sociologist Niklas Luhmann, who used a physical card index to write an enormous body of published work. The core insight is that the value of a note-taking system comes less from individual notes and more from the network of connections between them \u2014 which is exactly what a graph visualization like this one is trying to make visible. Tools like Obsidian are essentially digital slip boxes with search and backlinks built in, replacing Markdown files for index cards.",
      "path": "notes/tools/zettelkasten.md"
    }
  ],
  "links": [
    {
      "source": 0,
      "target": 4
    },
    {
      "source": 0,
      "target": 5
    },
    {
      "source": 1,
      "target": 6
    },
    {
      "source": 2,
      "target": 3
    },
    {
      "source": 2,
      "target": 4
    },
    {
      "source": 2,
      "target": 6
    },
    {
      "source": 2,
      "target": 13
    },
    {
      "source": 3,
      "target": 4
    },
    {
      "source": 4,
      "target": 5
    },
    {
      "source": 4,
      "target": 6
    },
    {
      "source": 4,
      "target": 13
    },
    {
      "source": 6,
      "target": 13
    },
    {
      "source": 7,
      "target": 9
    },
    {
      "source": 7,
      "target": 11
    },
    {
      "source": 8,
      "target": 10
    },
    {
      "source": 8,
      "target": 11
    },
    {
      "source": 9,
      "target": 11
    },
    {
      "source": 10,
      "target": 11
    },
    {
      "source": 12,
      "target": 13
    },
    {
      "source": 12,
      "target": 14
    },
    {
      "source": 13,
      "target": 14
    },
    {
      "source": 13,
      "target": 16
    },
    {
      "source": 13,
      "target": 17
    },
    {
      "source": 14,
      "target": 15
    },
    {
      "source": 14,
      "target": 16
    },
    {
      "source": 14,
      "target": 17
    },
    {
      "source": 14,
      "target": 18
    },
    {
      "source": 15,
      "target": 16
    },
    {
      "source": 16,
      "target": 17
    },
    {
      "source": 17,
      "target": 18
    },
    {
      "source": 17,
      "target": 19
    },
    {
      "source": 18,
      "target": 19
    }
  ]
};
