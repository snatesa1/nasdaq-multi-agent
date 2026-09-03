"""
test_socratic_session.py — Automated verification for Socratic Tutor session persistence.
Validates create, update, read, list, and delete operations on local SQLite.
"""

import pytest
from options_lab.api import db
from options_lab.api.models import SaveSessionRequest, UpdateSessionRequest, SocraticTutorRequest


def test_pydantic_save_session_request_no_session_id():
    """Verify frontend payload without session_id passes validation."""
    payload = {
        "title": "straddle call",
        "messages": [
            {"role": "assistant", "content": "Welcome to Socratic Tutor."},
            {"role": "user", "content": "Explain straddles."}
        ]
    }
    req = SaveSessionRequest(**payload)
    assert req.title == "straddle call"
    assert req.session_id is None
    assert len(req.messages) == 2


def test_pydantic_update_session_request_with_title():
    """Verify update payload with title passes validation."""
    payload = {
        "title": "Updated Straddle Topic",
        "messages": [
            {"role": "assistant", "content": "Updated."}
        ]
    }
    req = UpdateSessionRequest(**payload)
    assert req.title == "Updated Straddle Topic"
    assert len(req.messages) == 1


def test_pydantic_socratic_tutor_request():
    """Verify message or question passes validation."""
    req1 = SocraticTutorRequest(message="What is delta?")
    assert req1.message == "What is delta?"
    req2 = SocraticTutorRequest(question="What is gamma?")
    assert req2.question == "What is gamma?"


def test_sqlite_session_crud_lifecycle():
    """Verify complete SQLite session lifecycle: create -> read -> update -> list -> delete."""
    title = "Test Socratic Session - Automated"
    messages = [
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "Tell me about bull put spreads."}
    ]

    # 1. Create
    created = db.create_session(title=title, messages=messages)
    session_id = created["id"]
    assert session_id is not None
    assert created["title"] == title
    assert len(created["messages"]) == 2

    try:
        # 2. Read
        fetched = db.get_session(session_id)
        assert fetched is not None
        assert fetched["id"] == session_id
        assert fetched["title"] == title
        assert len(fetched["messages"]) == 2

        # 3. Update
        updated_messages = messages + [
            {"role": "assistant", "content": "A bull put spread is a credit spread."}
        ]
        updated = db.update_session(session_id, messages=updated_messages, title="Bull Put Spread Mastery")
        assert updated is not None
        assert updated["title"] == "Bull Put Spread Mastery"
        assert len(updated["messages"]) == 3

        # 4. List
        sessions_list = db.list_sessions()
        ids = [s["id"] for s in sessions_list]
        assert session_id in ids

    finally:
        # 5. Delete
        deleted = db.delete_session(session_id)
        assert deleted is True
        assert db.get_session(session_id) is None
