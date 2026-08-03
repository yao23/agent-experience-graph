# Nested response model leaks a field from a subclass

The response filter correctly removes undeclared fields from the outer model, but
it leaks `password` when a nested value is an instance of a more specific model.
This violates the declared response schema and can expose sensitive data.

Make the smallest production-code change that passes `python3 test_bug.py`.
Do not weaken or edit the test.
