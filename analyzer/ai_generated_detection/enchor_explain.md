The Pros and Cons of both Anchor methods:

1. Claims ➔ Description Anchor (The used method)
How it works: Give the AI the claims, ask it to write the description, then compare the generated description with the original description.

# PROS:

* Catches the #1 cheating method: Most people write short claims themselves and use AI to do the heavy lifting of padding out the 20-page description.
* Huge text sample: Comparing thousands of words gives the algorithm massive confidence in stylistic matches.
* Predictable AI "padding": When AI expands text, it uses highly predictable transitions ("Furthermore", "Moreover", "In some embodiments") which are very easy to match and detect.

# CONS:

* Slower/Expensive: Generating a long description takes the local LLM much more time and tokens.
* Misses Reverse-Cheaters: Won't detect if someone wrote the 20-page description by hand, but magically used AI just to summarize it into claims.

2. Description ➔ Claims Anchor (The Reverse)
How it works: Give the AI the description, ask it to write the claims, then compare claims.

# PROS:

* Very fast: Generating 10-15 claims takes almost no time or tokens for the LLM.
* Catches "Idea Translators": Great for catching inventors who just brain-dumped a description and asked the AI to "make this sound like legal patent claims."

# CONS:

* High False Negatives (Misses): There are many different ways to legally draft claims from the same description. Even if the original was AI, your detection-AI might choose a different legal angle, making them look different.

* Too short to compare: A few sentences of claims simply do not provide enough data points (verbs, adjectives, flow) to confidently prove AI generation. It's much harder to say "These two claims are stylistically identical" compared to analyzing a 15-page document.