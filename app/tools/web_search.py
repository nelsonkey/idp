"""Web search tool for answering specific questions.

Provides web search capability on top of the LLM's intelligence to answer
questions that require external or up-to-date information beyond document
analysis. This implementation serves as a structured search interface that
can be backed by various search providers.
"""

from strands import tool


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for information to answer specific questions.

    Use this tool when the user asks factual questions that require up-to-date
    information beyond document analysis, or when they need to cross-reference
    document content with external knowledge.

    Examples of queries this tool handles:
    - 'What are the latest IRS tax filing deadlines?'
    - 'Current FDA guidelines for clinical trial Phase III'
    - 'S&P 500 performance this quarter'

    Args:
        query: The search query string describing what information to find.
        max_results: Maximum number of search results to return (default: 5).

    Returns:
        A formatted string containing search results or a message indicating
        that a real search provider should be configured.
    """
    # NOTE: This is a placeholder implementation. To enable real web search,
    # integrate one of the following providers:
    #
    # Option 1 - Tavily (recommended for AI agents):
    #   from tavily import TavilyClient
    #   client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    #   results = client.search(query, max_results=max_results)
    #
    # Option 2 - SerpAPI:
    #   import serpapi
    #   results = serpapi.search(q=query, num=max_results)
    #
    # Option 3 - AWS Kendra (enterprise search):
    #   kendra = boto3.client('kendra')
    #   results = kendra.query(IndexId=..., QueryText=query)
    #
    # Option 4 - strands_tools built-in (if available):
    #   from strands_tools import http_request
    #
    # For now, this tool returns a structured response indicating the search
    # was requested, allowing the agent's LLM to synthesize an answer from
    # its training knowledge when no search provider is configured.

    return (
        f"## Web Search Results for: {query}\n\n"
        f"**Note:** No external search provider is currently configured. "
        f"The agent will use its built-in knowledge to answer this query.\n\n"
        f"**Query:** {query}\n"
        f"**Requested results:** {max_results}\n\n"
        f"Please configure a search provider (Tavily, SerpAPI, or AWS Kendra) "
        f"for real-time web search results. Set the appropriate API key in your "
        f"environment variables."
    )
