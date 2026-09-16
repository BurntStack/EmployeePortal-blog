import time

from django.db import connection


class ServerTimingMiddleware:
    """
    Adds a standard `Server-Timing` response header breaking total request
    time into DB time vs everything else (view logic, serialization,
    middleware, Django/Python import overhead on a cold serverless
    instance). Chrome DevTools' Network tab renders this natively - no log
    digging needed to see where request time actually goes.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        queries = []

        def wrapper(execute, sql, params, many, context):
            start = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                queries.append(time.perf_counter() - start)

        start = time.perf_counter()
        with connection.execute_wrapper(wrapper):
            response = self.get_response(request)
        total = time.perf_counter() - start

        db_time = sum(queries)
        response["Server-Timing"] = (
            f"db;dur={db_time * 1000:.1f};desc=\"{len(queries)} queries\", "
            f"app;dur={(total - db_time) * 1000:.1f}, "
            f"total;dur={total * 1000:.1f}"
        )
        return response
