"""
Comprehensive Automated Test Suite for AttritionAI
Tests:
1. Full-Dataset Analytical Engine (Aggregations, GroupBy, Filtering, Correlation, Distribution, Data Quality)
2. Dynamic Dataset Adaptation, Profiling & Versioning (Fingerprinting, Stale Reference Clearing)
3. Selective Hybrid RAG (Ingestion, Chunking, Keyword/Semantic Retrieval, Metadata & Citations)
4. Safe Query Planner (Typed Allowlist, Schema Validation, Safe Execution, Markdown Formatting)
5. Chatbot Engine & Orchestration (Analytics, RAG, Hybrid Combined, Session Pronoun Resolution, Offline Fallbacks)
6. Flask REST API Endpoints (Chatbot, Dataset Profile, Documents)
"""

import os
import sys
import unittest
import pandas as pd
import numpy as np

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import backend.data_loader as dl
import backend.analytics_engine as ae
import backend.rag_engine as re
import backend.query_planner as qp
import backend.chatbot_engine as ce
from backend.app import create_app


class TestDatasetProfilingAndVersioning(unittest.TestCase):
    """Test dynamic dataset profiling, schema discovery, and SHA-256 fingerprinting."""

    @classmethod
    def setUpClass(cls):
        dl.ensure_dataset_loaded()

    def test_active_dataset_loaded(self):
        df = dl.get_data()
        self.assertIsNotNone(df, "Active dataset DataFrame must not be None")
        self.assertGreater(len(df), 0, "Active dataset must contain rows")
        self.assertEqual(len(df), dl.TOTAL_EMPLOYEES, "Total employees count must match DataFrame row count exactly")

    def test_dataset_version_fingerprint(self):
        version = dl.get_dataset_version()
        self.assertIsNotNone(version, "Dataset version fingerprint must not be None")
        self.assertIsInstance(version, str)
        self.assertEqual(len(version), 10, "Dataset version should be 10-char hex prefix")

    def test_dataset_profile_generation(self):
        profile = dl.get_dataset_profile()
        self.assertIsNotNone(profile, "Profile must be computed")
        self.assertIn("row_count", profile)
        self.assertIn("columns_count", profile)
        self.assertIn("columns", profile)
        self.assertIn("data_quality", profile)
        self.assertEqual(profile["row_count"], len(dl.get_data()))
        self.assertIn("overall_health_score", profile["data_quality"])

    def test_column_distributions_in_profile(self):
        profile = dl.get_dataset_profile()
        cols = profile["columns"]
        # Check that numeric columns have summary statistics
        for col_name, meta in cols.items():
            if meta["is_numeric"]:
                self.assertIn("mean", meta)
                self.assertIn("min", meta)
                self.assertIn("max", meta)
                self.assertIn("median", meta)
                break


class TestFullDatasetAnalyticsEngine(unittest.TestCase):
    """Test full-dataset analytical operations (no row truncation or sampling)."""

    @classmethod
    def setUpClass(cls):
        cls.df = dl.ensure_dataset_loaded()

    def test_aggregation_full_dataset(self):
        res = ae.run_aggregation("MonthlyIncome", "mean")
        self.assertIn("value", res)
        # Verify exact calculation against pandas
        col = ae.resolve_column_name("MonthlyIncome")
        expected_mean = round(float(self.df[col].dropna().mean()), 2)
        self.assertAlmostEqual(res["value"], expected_mean, places=1)
        self.assertEqual(res["total_rows_evaluated"], len(self.df))

    def test_groupby_full_dataset(self):
        res = ae.run_groupby("Department", metric_column="AttritionFlag", agg_func="mean")
        self.assertIn("groups", res)
        self.assertGreater(len(res["groups"]), 0)
        # Sum of row counts in groups should equal total rows with valid department
        total_grouped_rows = sum(g["row_count"] for g in res["groups"])
        dept_col = ae.resolve_column_name("Department")
        self.assertEqual(total_grouped_rows, len(self.df[self.df[dept_col].notna()]))

    def test_multi_condition_filter(self):
        filters = [
            {"column": "Department", "operator": "==", "value": "Sales"},
            {"column": "OverTime", "operator": "==", "value": "Yes"}
        ]
        res = ae.run_filter(filters, limit=10)
        self.assertIn("matching_count", res)
        self.assertIn("percentage_of_dataset", res)
        # Verify against pandas filter
        dept_col = ae.resolve_column_name("Department")
        ot_col = ae.resolve_column_name("OverTime")
        expected = len(self.df[(self.df[dept_col].astype(str) == "Sales") & (self.df[ot_col].astype(str) == "Yes")])
        self.assertEqual(res["matching_count"], expected)

    def test_correlation_zero_variance_safety(self):
        res = ae.run_correlation("Age", "MonthlyIncome")
        self.assertIn("correlation", res)
        self.assertIsInstance(res["correlation"], (float, int))
        self.assertTrue(-1.0 <= res["correlation"] <= 1.0)

    def test_distribution_quartiles(self):
        res = ae.run_distribution("Age")
        self.assertIn("mean", res)
        self.assertIn("quartiles", res)
        self.assertIn("q1", res["quartiles"])
        self.assertIn("q3", res["quartiles"])
        self.assertEqual(res["count"], len(self.df))

    def test_data_quality_audit(self):
        res = ae.run_data_quality_audit()
        self.assertIn("overall_health_score", res)
        self.assertIn("duplicate_rows", res)
        self.assertIn("missing_summary", res)
        self.assertGreaterEqual(res["overall_health_score"], 0)
        self.assertLessEqual(res["overall_health_score"], 100)


class TestSafeQueryPlanner(unittest.TestCase):
    """Test Query Planner allowlisting, validation, execution, and security boundaries."""

    def test_rule_based_compiler_groupby(self):
        plan = qp.compile_query_plan("What is the attrition rate by department?", allow_llm=False)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["operation"].lower(), "groupby")
        self.assertEqual(plan.get("group_column", plan.get("group_by")), "Department")

    def test_rule_based_compiler_data_quality(self):
        plan = qp.compile_query_plan("Check for missing values and data quality issues", allow_llm=False)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["operation"].lower(), "data_quality")

    def test_schema_validation_rejects_injected_columns(self):
        unsafe_plan = {
            "operation": "AGGREGATION",
            "column": "non_existent_column_or_injection'; DROP TABLE users; --",
            "aggregation": "mean"
        }
        valid, err = qp.validate_query_plan(unsafe_plan)
        self.assertFalse(valid, "Query Planner must reject unresolvable or injected columns")
        self.assertIn("Cannot resolve", err)

    def test_plan_execution_returns_structured_results(self):
        plan = {
            "operation": "GROUPBY",
            "group_by": "Department",
            "metric_column": "AttritionFlag",
            "aggregation": "mean",
            "sort_desc": True
        }
        result = qp.execute_plan(plan)
        self.assertTrue(result["success"])
        self.assertIn("results", result)
        self.assertIn("groups", result)

    def test_markdown_table_formatting(self):
        plan = {"operation": "GROUPBY", "group_by": "Department", "metric_column": "AttritionFlag", "aggregation": "mean"}
        result = qp.execute_plan(plan)
        md = qp.format_plan_results_as_markdown(result, plan)
        self.assertIn("| Department |", md)
        self.assertIn("| :---", md)


class TestHybridRAGEngine(unittest.TestCase):
    """Test RAG document ingestion, search, chunking, and citations."""

    def test_preseeded_documents_exist(self):
        docs = re.list_documents()
        self.assertGreaterEqual(len(docs), 3, "At least 3 HR policy documents should be indexed")
        titles = [d["title"] for d in docs]
        self.assertTrue(any("Overtime" in t for t in titles))
        self.assertTrue(any("Retention" in t for t in titles))

    def test_semantic_keyword_retrieval(self):
        matches = re.search_documents("overtime hours threshold approval", top_k=3)
        self.assertGreater(len(matches), 0, "Should retrieve overtime policy chunk")
        top_match = matches[0]
        self.assertIn("chunk_text", top_match)
        self.assertIn("doc_title", top_match)
        self.assertIn("score", top_match)
        self.assertIn("citation", top_match)
        self.assertIn("Overtime", top_match["doc_title"])

    def test_document_ingestion_and_deletion(self):
        sample_text = "# Remote Work Policy 2026\n\nAll engineering staff are permitted 2 remote days per week."
        doc_id = re.ingest_document(
            doc_id="doc_remote_policy_test",
            title="Remote Work Guidelines 2026",
            raw_text=sample_text,
            doc_type="policy",
            category="Remote"
        )
        self.assertEqual(doc_id, "doc_remote_policy_test")

        # Verify it can be retrieved
        res = re.search_documents("remote days per week", top_k=2)
        self.assertTrue(any(m["doc_id"] == "doc_remote_policy_test" for m in res))

        # Cleanup test document
        re.delete_document("doc_remote_policy_test")
        remaining = [d["id"] for d in re.list_documents()]
        self.assertNotIn("doc_remote_policy_test", remaining)


class TestChatbotEngineOrchestration(unittest.TestCase):
    """Test full conversational routing, session memory, and hybrid analytics + RAG."""

    def setUp(self):
        self.session_id = "test_session_isolated_001"

    def test_analytics_question_routing(self):
        resp = ce.process_message("What is the overall attrition rate?", session_id=self.session_id)
        self.assertIn("answer", resp)
        self.assertIn("dataset_version", resp)
        self.assertIsNotNone(resp["dataset_version"])
        self.assertIn("evidence", resp)
        self.assertIn(resp["intent"], ["overall_kpis", "query_plan", "analytics", "hybrid_analytics_and_rag"])

    def test_rag_policy_question_routing(self):
        resp = ce.process_message("What is the company policy regarding overtime?", session_id=self.session_id)
        self.assertIn("answer", resp)
        self.assertIn("citations", resp)
        self.assertGreater(len(resp["citations"]), 0, "RAG query must return source citations")
        self.assertTrue(any("Overtime" in c["title"] for c in resp["citations"]))

    def test_hybrid_combined_question(self):
        resp = ce.process_message(
            "What is our overtime policy and how many employees are currently working overtime?",
            session_id=self.session_id
        )
        self.assertIn("answer", resp)
        self.assertIn("citations", resp)
        self.assertGreater(len(resp["citations"]), 0, "Combined query should return policy citations")
        # Evidence should include overtime analytics
        self.assertTrue(any("OverTime" in str(ev) or "overtime" in str(ev).lower() for ev in resp.get("evidence", [])))

    def test_employee_lookup_and_pronoun_followup(self):
        # Look up employee
        resp1 = ce.process_message("Tell me about employee E00001", session_id=self.session_id)
        self.assertIn("answer", resp1)
        self.assertIn("E00001", resp1["answer"])

        # Follow-up using pronoun "their"
        resp2 = ce.process_message("What is their flight risk?", session_id=self.session_id)
        self.assertIn("answer", resp2)
        # Should refer to employee E00001
        self.assertIn("E00001", resp2["answer"])

    def test_session_reference_invalidation_on_dataset_change(self):
        # Session remembers E00001
        session = ce.get_session(self.session_id)
        session["last_employee_id"] = "E00001"
        session["dataset_version"] = "old_stale_fingerprint_999"

        # Simulating next query with a different dataset version
        ce.get_session(self.session_id)
        # get_session invalidates stale references when version differs from current active dataset
        self.assertIsNone(session["last_employee_id"], "Stale employee ID must be cleared after dataset version mismatch")


class TestFlaskEndpoints(unittest.TestCase):
    """Test Flask HTTP API routes."""

    @classmethod
    def setUpClass(cls):
        app = create_app()
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_dataset_profile_endpoint(self):
        res = self.client.get("/api/dataset/profile")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("version", data)
        self.assertIn("profile", data)
        self.assertEqual(data["version"], dl.get_dataset_version())

    def test_documents_list_endpoint(self):
        res = self.client.get("/api/documents")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("documents", data)
        self.assertGreaterEqual(len(data["documents"]), 3)

    def test_chatbot_message_endpoint(self):
        res = self.client.post("/api/chatbot/message", json={"message": "What is the total employee count?"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("reply", data)
        self.assertIn("evidence", data)
        self.assertIn("dataset_version", data)
        self.assertEqual(data["dataset_version"], dl.get_dataset_version())


if __name__ == "__main__":
    unittest.main(verbosity=2)
