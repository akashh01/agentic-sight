"""agentic_sight — Agentic Sight: LangGraph-based video safety detector.

Two agents: the query optimizer agent (agent_graph.py) turns a
plain-language instruction into a structured detection task, and the
detection agent (detector_graph.py) runs tiered cheap/expensive vision
detection over sampled video frames.
"""
