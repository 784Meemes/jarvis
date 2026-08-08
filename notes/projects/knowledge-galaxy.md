# Knowledge Galaxy

The Knowledge Galaxy is an interactive 3D graph of this entire notes vault:
every Markdown file becomes a glowing node, colored by its folder, and
linked to every other note it mentions or [[wikilinks]] to. Built with
3D Force Graph running entirely in the browser off a CDN — no build step.

A small Python script (build.py) does the heavy lifting: it walks the
vault, extracts a title and excerpt from each file, and figures out the
edges by matching titles and wikilinks against every other note. The result
is graph-data.js, a static file the viewer loads directly.

It's part of the Jarvis Assistant project, and a proof that Git plus plain
Markdown is enough of a database to build something visually ambitious on
top of.
