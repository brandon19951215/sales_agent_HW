"""Backend checks with a scripted model; no API key or paid calls."""

import asyncio
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from backend.agent import build_graph, build_tools
from backend.main import app


class ScriptedModel:
    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        results = [m for m in messages if isinstance(m, ToolMessage)]
        if not results:
            return AIMessage(content="", tool_calls=[{
                "name": "lg_get_target", "args": {"region": "Singapore", "period": "2026-Q2"}, "id": "target"
            }])
        if len(results) == 1:
            assert results[0].content == "300"
            return AIMessage(content="", tool_calls=[{
                "name": "lg_calculate_variance", "args": {"actual": 200, "target": 300}, "id": "variance"
            }])
        assert results[-1].content == "-33.33"
        return AIMessage(content="Sales are 33.33% below target.")


class BackendChecks(unittest.TestCase):
    def test_graph_executes_tools_and_returns_to_model(self):
        graph = build_graph(ScriptedModel(), build_tools("http://127.0.0.1:8001/mcp"))
        result = asyncio.run(graph.ainvoke({"messages": [HumanMessage(content="Compare Q2")]}))
        self.assertEqual(result["messages"][-1].text, "Sales are 33.33% below target.")

    def test_http_validation_configuration_and_errors(self):
        # Patch dotenv loading so tests never read local credentials.
        with patch("backend.main.load_dotenv"), patch.dict(os.environ, {"OPENAI_API_KEY": "", "OPENAI_MODEL": ""}):
            with TestClient(app) as client:
                self.assertEqual(client.get("/health").json(), {"status": "ok", "agent_configured": False})
                self.assertEqual(client.post("/api/analyze", json={"prompt": "Compare Q2"}).status_code, 503)
                for body in [{}, {"prompt": ""}, {"prompt": "   "}, {"prompt": "x" * 4001}]:
                    self.assertEqual(client.post("/api/analyze", json=body).status_code, 422)

                class StubAgent:
                    async def analyze(self, prompt):
                        return "Sales are 33.33% below target."

                app.state.agent = StubAgent()
                response = client.post("/api/analyze", json={"prompt": "Compare Q2"})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"answer": "Sales are 33.33% below target."})

                class BrokenAgent:
                    async def analyze(self, prompt):
                        raise RuntimeError("sensitive upstream detail")

                app.state.agent = BrokenAgent()
                response = client.post("/api/analyze", json={"prompt": "Compare Q2"})
                self.assertEqual(response.status_code, 502)
                self.assertNotIn("sensitive", response.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
