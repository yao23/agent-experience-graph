# Path output crashes when the returned writer is called

`get_write_function()` accepts a `pathlib.Path` and returns a callback, but invoking
that callback raises a `NameError`. Make the smallest production-code change that
passes `python3 test_bug.py`. Do not weaken or edit the test.
