"""The notebook's LangGraph model/tool loop, without notebook state."""

from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from mcp import Client


TARGET_DATA = {"Singapore": {"2026-Q1": 200, "2026-Q2": 300, "2026-Q3": 400}}


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def build_tools(mcp_url: str):
    @tool
    async def mcp_get_sales(region: str, period: str):
        """Get actual sales for a region and period through MCP."""
        async with Client(mcp_url, read_timeout_seconds=20) as client:
            result = await client.call_tool(
                "get_sales", {"region": region, "period": period}
            )
            if result.is_error:
                raise RuntimeError("MCP sales tool failed")
            return result.content[0].text

    @tool
    def lg_get_target(region: str, period: str):
        """Get the sales target for a region and period."""
        if region not in TARGET_DATA:
            return {"error": f"Region '{region}' not found."}
        if period not in TARGET_DATA[region]:
            return {"error": f"Period '{period}' not found."}
        return TARGET_DATA[region][period]

    @tool
    def lg_calculate_variance(actual: float, target: float):
        """Calculate percentage variance between actual and target."""
        if target == 0:
            return {"error": "Target cannot be zero."}
        return round(((actual - target) / target) * 100, 2)

    return [mcp_get_sales, lg_get_target, lg_calculate_variance]


def build_graph(model, tools):
    model_with_tools = model.bind_tools(tools)

    async def model_node(state: AgentState):
        return {"messages": [await model_with_tools.ainvoke(state["messages"])]}

    def route_tools(state: AgentState):
        return "tools" if state["messages"][-1].tool_calls else END

    builder = StateGraph(AgentState)
    builder.add_node("model", model_node)
    builder.add_node("tools", ToolNode(tools, handle_tool_errors=False))
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", route_tools)
    builder.add_edge("tools", "model")
    return builder.compile()


class SalesAgent:
    def __init__(self, api_key: str, model_name: str, mcp_url: str):
        model = ChatOpenAI(
            api_key=api_key, model=model_name, use_responses_api=True,
            timeout=30, max_retries=1,
        )
        self.graph = build_graph(model, build_tools(mcp_url))

    async def analyze(self, prompt: str) -> str:
        result = await self.graph.ainvoke(
            {"messages": [
                SystemMessage(content=(
                    "You are a concise revenue analysis assistant. Use the tools "
                    "to retrieve sales and targets and calculate percentage variance. "
                    "If data is unavailable, explain the error; never invent figures."
                )),
                HumanMessage(content=prompt),
            ]},
            config={"recursion_limit": 10},
        )
        return result["messages"][-1].text
