import pytest

from zapros import BaseHandler, Client, Request, Response


class BrokenHandler(BaseHandler):
    def handle(self, request: Request) -> Response:
        raise RuntimeError("Error from BrokenHandler")


# the sync Client() has no default handler on Pyodide
@pytest.mark.no_pyodide
def test_handler_transform():
    with Client() as client:
        with pytest.raises(RuntimeError, match="Error from BrokenHandler"):
            client.get("https://example.com", handler=lambda _: BrokenHandler())


# the sync Client() has no default handler on Pyodide
@pytest.mark.no_pyodide
def test_handler_explicit():
    with Client() as client:
        with pytest.raises(RuntimeError, match="Error from BrokenHandler"):
            client.get("https://example.com", handler=BrokenHandler())


class CapturingHandler(BaseHandler):
    def __init__(self) -> None:
        self.requests: list[Request] = []

    def handle(self, request: Request) -> Response:
        self.requests.append(request)
        return Response(status=200)


def test_request_trailers_passed_through():
    handler = CapturingHandler()
    with Client(handler=handler) as client:
        client.post("https://example.com", body=b"hello", trailers={"X-Checksum": "abc"})
        client.get("https://example.com")

    assert handler.requests[0].trailers is not None
    assert handler.requests[0].trailers["x-checksum"] == "abc"
    assert handler.requests[1].trailers is None


def test_repeated_query_params_preserved():
    handler = CapturingHandler()
    with Client(handler=handler, default_params={"d": ["1", "2"], "k": "default"}) as client:
        client.get("https://example.com/?u=a&u=b&k=url", params={"c": ["x", "y"], "k": ["z", "w"]})
        client.get("https://example.com/?u=a&u=b")

    assert str(handler.requests[0].url) == "https://example.com/?d=1&d=2&u=a&u=b&c=x&c=y&k=z&k=w"
    assert str(handler.requests[1].url) == "https://example.com/?d=1&d=2&k=default&u=a&u=b"
