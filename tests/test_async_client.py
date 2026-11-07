import pytest

from zapros import AsyncBaseHandler, AsyncClient, Request, Response


class BrokenHandler(AsyncBaseHandler):
    async def ahandle(self, request: Request) -> Response:
        raise RuntimeError("Error from BrokenHandler")


# the sync Client() has no default handler on Pyodide
@pytest.mark.no_pyodide
async def test_handler_transform():
    async with AsyncClient() as client:
        with pytest.raises(RuntimeError, match="Error from BrokenHandler"):
            await client.get("https://example.com", handler=lambda _: BrokenHandler())


# the sync Client() has no default handler on Pyodide
@pytest.mark.no_pyodide
async def test_handler_explicit():
    async with AsyncClient() as client:
        with pytest.raises(RuntimeError, match="Error from BrokenHandler"):
            await client.get("https://example.com", handler=BrokenHandler())


class CapturingHandler(AsyncBaseHandler):
    def __init__(self) -> None:
        self.requests: list[Request] = []

    async def ahandle(self, request: Request) -> Response:
        self.requests.append(request)
        return Response(status=200)


async def test_request_trailers_passed_through():
    handler = CapturingHandler()
    async with AsyncClient(handler=handler) as client:
        await client.post("https://example.com", body=b"hello", trailers={"X-Checksum": "abc"})
        await client.get("https://example.com")

    assert handler.requests[0].trailers is not None
    assert handler.requests[0].trailers["x-checksum"] == "abc"
    assert handler.requests[1].trailers is None


async def test_repeated_query_params_preserved():
    handler = CapturingHandler()
    async with AsyncClient(handler=handler, default_params={"d": ["1", "2"], "k": "default"}) as client:
        await client.get("https://example.com/?u=a&u=b&k=url", params={"c": ["x", "y"], "k": ["z", "w"]})
        await client.get("https://example.com/?u=a&u=b")

    assert str(handler.requests[0].url) == "https://example.com/?d=1&d=2&u=a&u=b&c=x&c=y&k=z&k=w"
    assert str(handler.requests[1].url) == "https://example.com/?d=1&d=2&k=default&u=a&u=b"
