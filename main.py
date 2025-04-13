from contextlib import asynccontextmanager
import httpx
from typing import Any
from fastmcp import FastMCP, Context
from pydantic_settings import BaseSettings
from pydantic import Field
from urllib.parse import quote

import utils


class Settings(BaseSettings):
    base_url: str = Field(default=...)
    api_key: str = Field(default=...)


@asynccontextmanager
async def lifespan(app: FastMCP):
    """Lifespan context manager for FastMCP."""
    yield
    await httpClient.aclose()


settings = Settings()

mcp = FastMCP(name="teamsoverflow", lifespan=lifespan)
httpClient = httpx.AsyncClient()


async def make_so_request(url: str) -> dict[str, Any] | None:
    """Make a request to the StackOverflow API with proper error handling."""
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {settings.api_key}",
    }
    try:
        response = await httpClient.get(url, headers=headers, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error making request: {e}")
        return None


@mcp.tool()
async def search_stackoverflow(query: str, ctx: Context) -> utils.SearchExcerpts | str:
    """
    Search StackOverflow for a given query.
    :param query: the search query
    :return: A list of search results if successful, otherwise an error message.
    """
    # URL encode the query for safety
    await ctx.info(f"{settings.model_dump()}")

    encoded_query = quote(query)
    url = f"{settings.base_url}/search/excerpt?q={encoded_query}&page=1&pagesize=5&sort=relevance&answers=1"

    await ctx.info(f"Searching StackOverflow for: {query}")
    await ctx.info(f"Making request to {url}")

    data = await make_so_request(url)

    if not data:
        return "Unable to fetch results or no results found."

    try:
        results = utils.SearchExcerpts.model_validate(data)
        return results
    except Exception as e:
        await ctx.warning(f"Error parsing response: {e}")
        return f"Error parsing search results: {e}"


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")
