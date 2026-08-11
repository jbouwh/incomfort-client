"""Fixtures for incomfort backend library."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiohttp import web

from aiohttp.test_utils import TestServer
import pytest


@pytest.fixture(name="heater_list_exc")
def mock_heater_list_exception() -> Exception | None:
    """Mock a heater list exception."""
    return None


@pytest.fixture(name="heater_list")
def mock_heater_list() -> dict[str, list[str | None]] | str:
    """Mock a heater list."""
    return ""


@pytest.fixture(name="data_heater")
def mock_data_heater() -> dict[str, Any]:
    """Mock the heater data."""
    return {}


@pytest.fixture(name="gateway")
async def mock_gateway(
    aiohttp_server: Callable[[web.Application], Awaitable[TestServer]],
    heater_list: dict[str, list[str | None]] | str,
    data_heater: dict[str, Any],
    heater_list_exc: Exception | None,
) -> str:
    """Mock a gateway."""

    routes = web.RouteTableDef()

    @routes.get("/heaterlist.json")
    async def heater_list_hook(_request: web.Request) -> web.Response:
        if heater_list_exc:
            raise heater_list_exc
        if isinstance(heater_list, str):
            return web.Response(body=heater_list)
        return web.json_response(heater_list)

    @routes.get("/data.json")
    async def data_heater_hook(_request: web.Request) -> web.Response:
        return web.json_response(data_heater)

    app = web.Application()
    app.add_routes(routes)

    server = await aiohttp_server(app)
    return f"{server.host}:{server.port}"
