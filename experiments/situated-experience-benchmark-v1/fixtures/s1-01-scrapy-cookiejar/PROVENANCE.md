# Public provenance

- Project: Scrapy (`scrapy/scrapy`), BSD-3-Clause.
- Source bug: BugsInPy `scrapy-31`; buggy `5f02ef82e8560242eb34b336f385addfdef3211d`; human fix `dba7e39f61cbe2c22d3c9064f32f6e36d74f14b2` (2015-08-03).
- Transfer bug: BugsInPy `scrapy-19`; buggy `e328a9b9dfa4fbc79c59ed4f45f757e998301c31`; human fix `1f743996ff00a7b728d59b93d0967e1eb50072f0` (2016-02-07).
- Upstream evidence: <https://github.com/scrapy/scrapy/commit/dba7e39f61cbe2c22d3c9064f32f6e36d74f14b2> and <https://github.com/scrapy/scrapy/commit/1f743996ff00a7b728d59b93d0967e1eb50072f0>.

The staged files are dependency-free extracts of the named public production
methods and regression mechanisms. Names and behavioral assertions are retained
where needed for auditability; unrelated Scrapy code and dependencies are not
included. The controller validates both buggy failures and both human repairs.
