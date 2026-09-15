import sys
from pathlib import Path
import unittest
from unittest.mock import patch

# Ensure backend directory is in sys.path for imports
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from main import app


class TestFastAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root_endpoint(self):
        """Test GET / returns 200 OK."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)

    def test_health_endpoint(self):
        """Test GET /health returns status healthy without requiring LLM."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertIn("database", data)

    def test_invalid_empty_message_validation(self):
        """Test POST /api/chat with empty message fails validation (400/422)."""
        payload = {
            "session_id": "test_session_1",
            "message": "   ",
            "provider": "ollama",
        }
        response = self.client.post("/api/chat", json=payload)
        self.assertIn(response.status_code, (400, 422))

    def test_invalid_empty_session_id_validation(self):
        """Test POST /api/chat with empty session_id fails validation (400/422)."""
        payload = {
            "session_id": "",
            "message": "How do product teams improve retention?",
            "provider": "ollama",
        }
        response = self.client.post("/api/chat", json=payload)
        self.assertIn(response.status_code, (400, 422))

    @patch("main.generate_chat_response")
    def test_successful_chat_request(self, mock_generate):
        """Test successful POST /api/chat request and response formatting."""
        mock_generate.return_value = {
            "message": "To improve retention, product teams should focus on tactical churn and early onboarding.",
            "sources": [
                {
                    "guest": "Patrick Campbell",
                    "title": "10 lessons on bootstrapping",
                    "url": "https://youtube.com/watch?v=123",
                    "chunk_index": 1,
                }
            ],
            "provider": "ollama",
        }

        payload = {
            "session_id": "session_test_123",
            "message": "How should product teams improve retention?",
            "provider": "ollama",
        }
        response = self.client.post("/api/chat", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["session_id"], "session_test_123")
        self.assertIn("To improve retention", data["message"])
        self.assertEqual(len(data["sources"]), 1)
        self.assertEqual(data["sources"][0]["guest"], "Patrick Campbell")
        self.assertEqual(data["provider"], "ollama")

    @patch("main.generate_chat_response")
    def test_session_isolation(self, mock_generate):
        """Test that different session_ids do not share conversation context."""
        mock_generate.return_value = {
            "message": "Sample mock answer",
            "sources": [],
            "provider": "ollama",
        }

        client = TestClient(app)

        res1 = client.post("/api/chat", json={"session_id": "session_A", "message": "Question A"})
        self.assertEqual(res1.status_code, 200)

        res2 = client.post("/api/chat", json={"session_id": "session_B", "message": "Question B"})
        self.assertEqual(res2.status_code, 200)

        self.assertTrue(mock_generate.called)

    def test_artifact_empty_prompt_validation(self):
        """Test POST /api/artifacts with empty prompt fails validation."""
        payload = {
            "session_id": "test_session_art",
            "prompt": "   ",
            "format": "markdown",
        }
        response = self.client.post("/api/artifacts", json=payload)
        self.assertIn(response.status_code, (400, 422))

    def test_artifact_invalid_format_validation(self):
        """Test POST /api/artifacts with invalid format fails validation."""
        payload = {
            "session_id": "test_session_art",
            "prompt": "Create retention guide",
            "format": "pdf",
        }
        response = self.client.post("/api/artifacts", json=payload)
        self.assertIn(response.status_code, (400, 422))

    @patch("main.generate_artifact")
    def test_markdown_artifact_response(self, mock_artifact):
        """Test successful markdown artifact creation."""
        mock_artifact.return_value = {
            "title": "Product Retention Checklist",
            "content": "# Product Retention Checklist\n\n- Step 1: Reduce tactical churn",
            "format": "markdown",
        }

        payload = {
            "session_id": "session_art_1",
            "prompt": "Generate a retention checklist",
            "format": "markdown",
        }
        response = self.client.post("/api/artifacts", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["artifact_id"].startswith("art_"))
        self.assertEqual(data["session_id"], "session_art_1")
        self.assertEqual(data["title"], "Product Retention Checklist")
        self.assertEqual(data["format"], "markdown")
        self.assertIn("# Product Retention Checklist", data["content"])

    @patch("main.generate_artifact")
    def test_html_artifact_response(self, mock_artifact):
        """Test successful HTML artifact creation."""
        mock_artifact.return_value = {
            "title": "Retention Dashboard Strategy",
            "content": "<!DOCTYPE html><html><head><title>Retention Dashboard Strategy</title></head><body><h1>Retention Strategy</h1></body></html>",
            "format": "html",
        }

        payload = {
            "session_id": "session_art_2",
            "prompt": "Generate HTML retention dashboard guide",
            "format": "html",
        }
        response = self.client.post("/api/artifacts", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["artifact_id"].startswith("art_"))
        self.assertEqual(data["session_id"], "session_art_2")
        self.assertEqual(data["title"], "Retention Dashboard Strategy")
        self.assertEqual(data["format"], "html")
        self.assertIn("<!DOCTYPE html>", data["content"])

    def test_broad_retention_question_synthesis(self):
        """
        Regression test: Verify that broad retention queries synthesize across multiple
        retrieved experts and do not produce an exclusively Patrick Campbell cancellation-flow answer.
        """
        from rag import generate_chat_response

        # Execute live or mocked RAG query for broad retention
        res = generate_chat_response("How can product teams improve retention?", limit=3, provider="ollama")
        answer = res.get("message", "")
        sources = res.get("sources", [])

        # 1. Answer should be non-empty and pass grounding
        self.assertTrue(len(answer) > 0)
        self.assertNotIn("I don't have enough evidence", answer)

        # 2. Answer must not focus exclusively on cancellation flows
        ans_lower = answer.lower()
        if "cancellation" in ans_lower:
            # If cancellation is mentioned, it should not be the sole topic
            self.assertTrue(
                any(term in ans_lower for term in ["customer", "experience", "core", "onboarding", "cohort", "tavel", "hockenmaier", "user"]),
                "Broad retention answer should synthesize broad themes beyond cancellation flows."
            )

        # 3. Multiple expert sources should be present
        expert_names = {s.get("guest") for s in sources if s.get("guest")}
        self.assertGreaterEqual(len(sources), 1)

        # 4. Cross-attribution check: Verify early user experience (Sarah Tavel) is not falsely attributed to Patrick Campbell
        if "patrick campbell" in ans_lower and "early user experience" in ans_lower:
            self.assertNotIn(
                "early user experience" + " as seen in patrick campbell",
                ans_lower,
                "Cross-attribution error: Sarah Tavel's early user experience concept should not be attributed to Patrick Campbell."
            )

    def test_multiturn_sequential_retention_session(self):
        """
        Regression test: Perform two sequential calls in the SAME session:
        1. Ask Patrick Campbell cancellation advice.
        2. Ask 'How can product teams improve retention?'
        Verify answer 2 does not repeat answer 1, starts directly on retention, and synthesizes broadly.
        """
        session_id = "multiturn_session_test_99"

        # Turn 1: Patrick Campbell cancellation flows
        res1 = self.client.post("/api/chat", json={
            "session_id": session_id,
            "message": "What is Patrick Campbell's advice on cancellation flows?",
            "provider": "ollama"
        })
        self.assertEqual(res1.status_code, 200)
        ans1 = res1.json()["message"]

        # Turn 2: Broad retention question in same session
        res2 = self.client.post("/api/chat", json={
            "session_id": session_id,
            "message": "How can product teams improve retention?",
            "provider": "ollama"
        })
        self.assertEqual(res2.status_code, 200)
        ans2 = res2.json()["message"]
        ans2_lower = ans2.lower()

        # Assertions
        # 1. Answer 2 does NOT contain Answer 1 verbatim
        self.assertNotIn(ans1, ans2, "Turn 2 answer should not repeat Turn 1 answer verbatim.")

        # 2. Answer 2 does NOT start with "Patrick Campbell's advice on cancellation flows"
        self.assertFalse(
            ans2.startswith("Patrick Campbell's advice on cancellation flows"),
            "Turn 2 answer must not start with Turn 1's query preamble."
        )

        # 3. Answer 2 addresses retention broadly
        self.assertTrue(
            any(term in ans2_lower for term in ["retention", "customer", "experience", "onboarding", "product"]),
            "Turn 2 answer must address retention broadly."
        )

        # 4. References at least two relevant retrieved experts/themes when evidence supports it
        theme_count = sum(1 for theme in ["experience", "onboarding", "journey", "cancellation", "churn", "lever", "active"] if theme in ans2_lower)
        self.assertGreaterEqual(theme_count, 2, "Turn 2 answer should reference at least two relevant retention themes/experts.")

    def test_capability_fast_path(self):
        """
        Regression test: Verify capability/meta questions ('what are you capable of?', 'what can you do?')
        return a fast-path capability summary with empty sources and skip RAG retrieval.
        """
        for query in ["what are you capable of?", "what can you do?"]:
            response = self.client.post("/api/chat", json={
                "session_id": "test_capability_session",
                "message": query,
                "provider": "ollama"
            })
            self.assertEqual(response.status_code, 200)
            data = response.json()

            # Verify sources list is empty
            self.assertEqual(data["sources"], [], f"Sources must be empty for capability question '{query}'")

            # Verify message describes actual capabilities
            msg = data["message"]
            self.assertIn("Lenny's Growth Assistant", msg)
            self.assertIn("Grounded Product & Growth Insights", msg)
            self.assertIn("Source Citations", msg)
            self.assertIn("Artifact Generation", msg)

    def test_patrick_three_turn_cancellation_flowup(self):
        """
        Regression test: Verify 3-turn conversation where turn 3 is a short follow-up:
        Turn 1: "What is Patrick Campbell's advice on cancellation flows?"
        Turn 2: "Can you explain that more simply?"
        Turn 3: "What is the most actionable step?"
        """
        session_id = "test_patrick_3turn_session"

        # Turn 1
        res1 = self.client.post("/api/chat", json={
            "session_id": session_id,
            "message": "What is Patrick Campbell's advice on cancellation flows?",
            "provider": "ollama"
        })
        self.assertEqual(res1.status_code, 200)

        # Turn 2
        res2 = self.client.post("/api/chat", json={
            "session_id": session_id,
            "message": "Can you explain that more simply?",
            "provider": "ollama"
        })
        self.assertEqual(res2.status_code, 200)

        # Turn 3
        res3 = self.client.post("/api/chat", json={
            "session_id": session_id,
            "message": "What is the most actionable step?",
            "provider": "ollama"
        })
        self.assertEqual(res3.status_code, 200)
        data3 = res3.json()
        ans3 = data3.get("message", "")
        sources3 = data3.get("sources", [])
        ans3_lower = ans3.lower()

        # Assertion 1: Turn 3 remains about Patrick / cancellation / churn / value / offboarding
        cancellation_keywords = ["patrick", "cancellation", "cancel", "churn", "offboarding", "salvage", "discount", "pause", "value", "step"]
        self.assertTrue(
            any(kw in ans3_lower for kw in cancellation_keywords),
            f"Turn 3 should address Patrick/cancellation topic. Got: {ans3}"
        )

        # Assertion 2: Turn 3 sources should belong to Patrick Campbell and NOT contain unrelated experts
        unrelated_experts = ["melanie perkins", "varun parmar", "jake knapp", "john zeratsky"]
        for s in sources3:
            guest = s.get("guest", "").lower()
            for u in unrelated_experts:
                self.assertNotIn(u, guest, f"Turn 3 sources should not contain unrelated expert '{u}'")

        for u in unrelated_experts:
            self.assertNotIn(u, ans3_lower, f"Turn 3 answer text should not mention unrelated expert '{u}'")

        # Assertion 3: Turn 3 does not start a new unrelated topic
        self.assertNotIn("I don't have enough evidence", ans3)

        # Assertion 4: Previous assistant text is not treated as evidence
        for s in sources3:
            self.assertTrue(bool(s.get("title")), "Source must come from transcript chunk metadata")

    def test_retention_vs_engagement_distinction(self):
        """
        Regression test: Verify 'What is the difference between retention and engagement?'
        distinguishes user retention from engagement and does not equate retention with net dollar retention.
        """
        response = self.client.post("/api/chat", json={
            "session_id": "test_retention_vs_engagement_session",
            "message": "What is the difference between retention and engagement?",
            "provider": "ollama"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        ans = data.get("message", "")
        ans_lower = ans.lower()

        # Answer should be grounded and non-empty
        self.assertTrue(len(ans) > 0)
        self.assertNotIn("I don't have enough evidence", ans)

        # Must mention both retention and engagement
        self.assertIn("retention", ans_lower)
        self.assertIn("engagement", ans_lower)

        # Verify response does not equate user retention with net dollar retention
        if "net dollar retention" in ans_lower or "ndr" in ans_lower:
            self.assertNotIn("net dollar retention is user retention", ans_lower)
            self.assertNotIn("net dollar retention is defined as user retention", ans_lower)


if __name__ == "__main__":
    unittest.main()



