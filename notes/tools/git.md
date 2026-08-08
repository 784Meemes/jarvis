# Git

Git is a distributed version control system: every clone is a full copy of
the project's history, and commits are content-addressed snapshots linked
into a graph rather than a simple linear diff chain. Branching and merging
are cheap, which is what enables the whole pull-request workflow.

[[GitHub]] is the most popular hosting service built on top of Git, adding
code review, issue tracking, and CI on top of the underlying protocol. This
notes vault itself lives in a Git repository, versioned right alongside the
script that turns it into a graph.
