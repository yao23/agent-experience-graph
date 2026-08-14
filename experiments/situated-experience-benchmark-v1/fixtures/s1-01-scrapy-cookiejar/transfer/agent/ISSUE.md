# Python 3 CookieJar adapter migration

The standard-library CookieJar contract changed on Python 3: it reads request
state through attributes that native urllib request objects expose. This
adapter still exposes only the older method-shaped interface, so cookie
processing raises `AttributeError` even though the equivalent values exist.

Reproduce the public failure, make the smallest production-only repair in
`cookie_adapter.py`, and run the public test. Do not modify tests or inspect
outside this repository.
