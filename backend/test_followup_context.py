import sys
import os
import unittest

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag import contextualize_query, generate_chat_response, analyze_query, select_evidence


class TestFollowupContextualization(unittest.TestCase):
    def test_case_a_dan_hockenmaier_followup(self):
        """
        Test A:
        Previous: "What are core product levers according to Dan Hockenmaier?"
        Follow-up: "explain the above in simple terms"
        Expected retrieval: Dan Hockenmaier sources.
        """
        history = [
            {"role": "user", "content": "What are core product levers according to Dan Hockenmaier?"},
            {"role": "assistant", "content": "Dan Hockenmaier explains that core product levers include early user experience..."}
        ]
        question = "explain the above in simple terms"

        retrieval_query = contextualize_query(question, history)
        self.assertIn("Dan Hockenmaier", retrieval_query)
        self.assertIn("core product levers", retrieval_query)

        analysis = analyze_query(retrieval_query)
        self.assertEqual(analysis["expert"], "Dan Hockenmaier")

        results, expert_substantive = select_evidence(retrieval_query, analysis, limit=3)
        self.assertTrue(len(results) > 0)
        guests = [getattr(r, "episode", "") for r in results]
        self.assertIn("Dan Hockenmaier", guests)
        print("\n[TEST A PASS] Retrieved Dan Hockenmaier sources:", guests)

    def test_case_b_retention_followup(self):
        """
        Test B:
        Previous: "How can product teams improve retention?"
        Follow-up: "Can you explain that more simply?"
        Expected: retention-related sources.
        """
        history = [
            {"role": "user", "content": "How can product teams improve retention?"},
            {"role": "assistant", "content": "Product teams can improve retention by focusing on core actions..."}
        ]
        question = "Can you explain that more simply?"

        retrieval_query = contextualize_query(question, history)
        self.assertIn("retention", retrieval_query.lower())

        analysis = analyze_query(retrieval_query)
        self.assertIn("retention", analysis["topic_tokens"])

        results, _ = select_evidence(retrieval_query, analysis, limit=3)
        self.assertTrue(len(results) > 0)
        contents = " ".join([getattr(r, "content", "").lower() for r in results])
        self.assertTrue("retention" in contents or "retain" in contents)
        print("[TEST B PASS] Retention context preserved in retrieval query:", retrieval_query)

    def test_case_c_sarah_tavel_followup(self):
        """
        Test C:
        Previous: "What does Sarah Tavel say about measuring retention?"
        Follow-up: "Why is that important?"
        Expected: Sarah Tavel + retention context.
        """
        history = [
            {"role": "user", "content": "What does Sarah Tavel say about measuring retention?"},
            {"role": "assistant", "content": "Sarah Tavel emphasizes measuring cohort retention and smile graphs..."}
        ]
        question = "Why is that important?"

        retrieval_query = contextualize_query(question, history)
        self.assertIn("Sarah Tavel", retrieval_query)

        analysis = analyze_query(retrieval_query)
        self.assertEqual(analysis["expert"], "Sarah Tavel")

        results, _ = select_evidence(retrieval_query, analysis, limit=3)
        self.assertTrue(len(results) > 0)
        guests = [getattr(r, "episode", "") for r in results]
        self.assertIn("Sarah Tavel", guests)
        print("[TEST C PASS] Retrieved Sarah Tavel sources for follow-up:", guests)

    def test_case_d_patrick_campbell_independent(self):
        """
        Test D:
        New independent query: "What is Patrick Campbell's advice on cancellation flows?"
        Expected: Patrick sources.
        """
        history = [
            {"role": "user", "content": "How can product teams improve retention?"},
            {"role": "assistant", "content": "Product teams can focus on activation..."}
        ]
        question = "What is Patrick Campbell's advice on cancellation flows?"

        retrieval_query = contextualize_query(question, history)
        # Should NOT inherit previous retention query context because it's a new independent query
        self.assertEqual(retrieval_query, question)

        analysis = analyze_query(retrieval_query)
        self.assertEqual(analysis["expert"], "Patrick Campbell")

        results, _ = select_evidence(retrieval_query, analysis, limit=3)
        self.assertTrue(len(results) > 0)
        guests = [getattr(r, "episode", "") for r in results]
        self.assertIn("Patrick Campbell", guests)
        print("[TEST D PASS] Retrieved Patrick Campbell sources for independent query:", guests)

    def test_case_e_new_session_anaphoric_query(self):
        """
        Test E:
        New session: "Explain the above in simple terms"
        Expected: no inherited context and safe handling.
        """
        history = []
        question = "Explain the above in simple terms"

        retrieval_query = contextualize_query(question, history)
        self.assertEqual(retrieval_query, question)

        result = generate_chat_response(question, conversation_history=history, limit=3)
        self.assertIn("message", result)
        print("[TEST E PASS] New session handled safely without error. Output message length:", len(result["message"]))


if __name__ == "__main__":
    unittest.main()
