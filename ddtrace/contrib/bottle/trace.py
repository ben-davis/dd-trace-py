
# 3p
from bottle import response, request

# stdlib
import ddtrace
from ddtrace.ext import http, AppTypes
from ...propagation.http import HTTPPropagator

class TracePlugin(object):

    name = 'trace'
    api = 2

    def __init__(self, service="bottle", tracer=None, distributed_tracing_enabled=False):
        self.service = service
        self.tracer = tracer or ddtrace.tracer
        self.tracer.set_service_info(
            service=service,
            app="bottle",
            app_type=AppTypes.web)
        self.distributed_tracing_enabled = distributed_tracing_enabled

    def apply(self, callback, route):

        def wrapped(*args, **kwargs):
            if not self.tracer or not self.tracer.enabled:
                return callback(*args, **kwargs)

            resource = "%s %s" % (request.method, request.route.rule)

            with self.tracer.trace("bottle.request", service=self.service, resource=resource) as s:
                code = 0

                # Propagate headers such as x-datadog-trace-id.
                if self.distributed_tracing_enabled:
                    propagator = HTTPPropagator()
                    context = propagator.extract(self.headers)
                    if context.trace_id:
                        self.tracer.context_provider.activate(context)

                try:
                    return callback(*args, **kwargs)
                except Exception:
                    # bottle doesn't always translate unhandled exceptions, so
                    # we mark it here.
                    code = 500
                    raise
                finally:
                    s.set_tag(http.STATUS_CODE, code or response.status_code)
                    s.set_tag(http.URL, request.path)
                    s.set_tag(http.METHOD, request.method)

        return wrapped
