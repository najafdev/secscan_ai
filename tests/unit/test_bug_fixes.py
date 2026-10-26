# SecScan AI core module
"""Regression unit tests for bug fixes."""

import os
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest

from database import get_db_manager, PentestSession
from security.authentication import ComplianceAuditLogger, EnterpriseAuth
from ai_engine.advanced_engine import PatternRecognizer, AdvancedAIEngine
from performance.parallel_processor import TaskQueue, Task, TaskStatus, ParallelProcessor
from advance_secscan_ai import (
    EnterpriseSecScanAI,
    PentestingPhases,
    EnterprisePentestingPhases,
    AIEngine,
    ToolManager,
)


def test_compliance_audit_logger_fallback(tmp_path, monkeypatch):
    """Test that ComplianceAuditLogger creates missing dir or falls back cleanly."""
    custom_log = tmp_path / "custom_dir" / "audit.log"
    monkeypatch.setenv("AUDIT_LOG_FILE", str(custom_log))
    
    logger = ComplianceAuditLogger()
    assert logger.logger is not None
    assert custom_log.exists()
    
    # Test permission error fallback to local logs/
    monkeypatch.setenv("AUDIT_LOG_FILE", "/root/forbidden_path/audit.log")
    with patch("pathlib.Path.mkdir", side_effect=PermissionError("Denied")):
        logger_fallback = ComplianceAuditLogger()
        assert logger_fallback.logger is not None


def test_pattern_recognizer_truth_value():
    """Verify that PatternRecognizer.detect_patterns does not raise ValueError on sparse matrices."""
    recognizer = PatternRecognizer()
    # Test text containing known indicators
    results = recognizer.detect_patterns("SELECT * FROM users WHERE id = '1' or '1'='1' error in SQL syntax")
    assert isinstance(results, list)
    assert len(results) > 0
    assert any(p[0].pattern_id == "sql_injection" for p in results)

    # Test text with no indicators
    empty_results = recognizer.detect_patterns("harmless benign string")
    assert isinstance(empty_results, list)


def test_structure_analysis_confidence_score_percentages():
    """Verify confidence score parsing handles percentages properly."""
    engine = AdvancedAIEngine()
    sample_text = (
        "Summary: Web scan detected vulnerabilities.\n"
        "Confidence: 85%\n"
        "Recommendations:\n"
        "- Patch database\n"
        "Next actions:\n"
        "- Run retest\n"
    )
    res = engine._structure_analysis(sample_text, [])
    assert abs(res.confidence_score - 0.85) < 0.01


def test_task_queue_equal_priority_and_timestamp():
    """Verify TaskQueue does not crash with TypeError when tasks have identical priority and timestamp."""
    queue = TaskQueue()
    fixed_time = datetime(2026, 1, 1, 12, 0, 0)
    
    task1 = Task(
        task_id="task-1",
        function_name="dummy",
        args=(),
        kwargs={},
        priority=1,
        created_at=fixed_time,
    )
    task2 = Task(
        task_id="task-2",
        function_name="dummy",
        args=(),
        kwargs={},
        priority=1,
        created_at=fixed_time,
    )
    
    # Adding tasks with identical priority & created_at must not raise TypeError
    queue.put(task1)
    queue.put(task2)
    
    retrieved1 = queue.get()
    retrieved2 = queue.get()
    assert {retrieved1.task_id, retrieved2.task_id} == {"task-1", "task-2"}


def test_task_queue_cancelled_status_in_get_result():
    """Verify get_task_result raises RuntimeError when task is marked CANCELLED."""
    processor = ParallelProcessor()
    task = Task(
        task_id="task-cancelled",
        function_name="dummy",
        args=(),
        kwargs={},
        status=TaskStatus.CANCELLED,
    )
    processor.task_queue.tasks[task.task_id] = task
    
    with pytest.raises(RuntimeError, match="cancelled"):
        processor.get_task_result("task-cancelled", timeout=1)


def test_pentesting_phases_backward_compatibility():
    """Verify PentestingPhases supports legacy (ai, tools, target, scope, auth_key) signature."""
    ai = AIEngine()
    tools = ToolManager()
    phases = PentestingPhases(ai, tools, "192.168.1.1", "test scope", "SECRET-KEY")
    
    assert phases.target_info["target"] == "192.168.1.1"
    assert phases.target_info["scope"] == "test scope"
    assert phases.target_info["auth_key"] == "SECRET-KEY"
    assert phases.session_id is not None


def test_database_session_assessment_type():
    """Verify PentestSession model and manager define assessment_type."""
    import ast
    from pathlib import Path

    models_path = Path(__file__).resolve().parent.parent.parent / "database" / "models.py"
    with open(models_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(models_path))
    
    found_assessment_type = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "PentestSession":
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id == "assessment_type":
                            found_assessment_type = True
    assert found_assessment_type, "assessment_type Column not found on PentestSession model"

    manager_path = Path(__file__).resolve().parent.parent.parent / "database" / "manager.py"
    with open(manager_path, "r", encoding="utf-8") as f:
        mgr_tree = ast.parse(f.read(), filename=str(manager_path))
    
    found_mgr_param = False
    for node in ast.walk(mgr_tree):
        if isinstance(node, ast.FunctionDef) and node.name == "create_pentest_session":
            arg_names = [arg.arg for arg in node.args.args]
            if "assessment_type" in arg_names:
                found_mgr_param = True
    assert found_mgr_param, "assessment_type parameter not found in create_pentest_session"


def test_enterprise_secscan_ai_menu_methods():
    """Verify all previously missing EnterpriseSecScanAI menu methods exist and execute without AttributeError."""
    app = EnterpriseSecScanAI()
    assert hasattr(app, "run_specific_phase")
    assert hasattr(app, "run_custom_workflow")
    assert hasattr(app, "view_reports_analytics")
    assert hasattr(app, "generate_executive_summary")
    assert hasattr(app, "start_realtime_dashboard")
    assert hasattr(app, "manage_users_permissions")
    assert hasattr(app, "system_configuration")
    assert hasattr(app, "compliance_management")
    assert hasattr(app, "configure_ai_engine")
    assert hasattr(app, "manage_tools")
    assert hasattr(app, "voice_command_mode")

    # Verify non-interactive executions of inspection methods
    app.system_configuration()
    app.compliance_management()
    app.configure_ai_engine()
    app.view_reports_analytics()
