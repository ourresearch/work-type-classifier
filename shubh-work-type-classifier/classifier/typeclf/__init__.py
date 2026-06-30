"""typeclf — a lightweight, deployable work-type classifier (linear, no LLM, no neural net).

Distills the Opus 4.8 gold labels (produced by ../labeler) into a multinomial logistic
regression over TF-IDF text + a few structured signals. Two feature scopes:
  - "full":     uses taxicab/landing signals (accuracy ceiling; needs the enrich step)
  - "metadata": OpenAlex-native fields only (runs offline at full-corpus scale)
"""
__version__ = "0.1.0"
