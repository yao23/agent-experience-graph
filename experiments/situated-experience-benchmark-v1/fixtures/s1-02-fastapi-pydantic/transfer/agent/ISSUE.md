# Pydantic collection representation migration

FastAPI form extraction recognizes typing-based sequence fields but loses
repeated values when Pydantic represents an equivalent annotation as a concrete
built-in `list`, `set`, or `tuple` class. Under this dependency representation,
the field shape can remain scalar even though its concrete type is a sequence.

Reproduce the public failure, preserve scalar and typing-based behavior, make
the smallest production-only repair in `form_extractor.py`, and run the public
test. Do not modify tests or inspect outside this repository.
