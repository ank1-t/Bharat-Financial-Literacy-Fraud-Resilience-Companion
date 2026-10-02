"""
tests/test_quiz.py
───────────────────
Unit tests for the adaptive quiz engine.
Verifies difficulty escalation, session state management, and scoring.
"""

import pytest
from quiz.quiz_engine import QuizSession, TOTAL_QUESTIONS, SCORE_BADGES
from quiz.questions import QUESTIONS, get_questions_by_difficulty, get_question_by_id


class TestQuestionBank:
    """Tests for the question bank data integrity."""

    def test_questions_exist(self):
        assert len(QUESTIONS) >= 6, "Need at least 6 questions (2 per difficulty)"

    def test_all_difficulty_levels_present(self):
        for level in [1, 2, 3]:
            qs = get_questions_by_difficulty(level)
            assert len(qs) >= 1, f"No questions at difficulty level {level}"

    def test_all_questions_have_required_fields(self):
        required_fields = [
            "id", "difficulty", "text_en", "text_hi",
            "options_en", "options_hi", "correct",
            "explanation_en", "explanation_hi", "source"
        ]
        for q in QUESTIONS:
            for field in required_fields:
                assert field in q, f"Question {q.get('id','?')} missing field: {field}"

    def test_correct_index_in_range(self):
        for q in QUESTIONS:
            assert 0 <= q["correct"] < len(q["options_en"]), \
                f"Question {q['id']} has invalid correct index"

    def test_options_count(self):
        for q in QUESTIONS:
            assert len(q["options_en"]) == 4, f"Question {q['id']} should have 4 options"
            assert len(q["options_hi"]) == 4, f"Question {q['id']} Hindi options should have 4"

    def test_unique_question_ids(self):
        ids = [q["id"] for q in QUESTIONS]
        assert len(ids) == len(set(ids)), "Duplicate question IDs found"

    def test_get_question_by_id(self):
        first_id = QUESTIONS[0]["id"]
        result = get_question_by_id(first_id)
        assert result is not None
        assert result["id"] == first_id

    def test_get_question_by_invalid_id(self):
        result = get_question_by_id("nonexistent_id")
        assert result is None


class TestQuizSession:
    """Tests for QuizSession adaptive logic."""

    def test_initial_state(self):
        session = QuizSession()
        assert session.current_difficulty == 1
        assert session.score == 0
        assert session.is_complete is False
        assert session.questions_asked == []

    def test_correct_answer_increases_difficulty(self):
        session = QuizSession()
        question = session.get_next_question()
        assert question is not None

        result = session.submit_answer(question, question["correct"])
        assert result["is_correct"] is True
        assert session.current_difficulty == 2  # escalated from 1 → 2

    def test_wrong_answer_stays_at_difficulty(self):
        session = QuizSession()
        question = session.get_next_question()
        assert question is not None

        wrong_index = (question["correct"] + 1) % 4
        result = session.submit_answer(question, wrong_index)
        assert result["is_correct"] is False
        assert session.current_difficulty == 1  # stays at 1

    def test_difficulty_caps_at_3(self):
        session = QuizSession()
        session.current_difficulty = 3
        question = session.get_next_question()
        if question:
            session.submit_answer(question, question["correct"])
        assert session.current_difficulty <= 3

    def test_score_increments_on_correct(self):
        session = QuizSession()
        question = session.get_next_question()
        session.submit_answer(question, question["correct"])
        assert session.score == 1

    def test_score_does_not_increment_on_wrong(self):
        session = QuizSession()
        question = session.get_next_question()
        wrong_idx = (question["correct"] + 1) % 4
        session.submit_answer(question, wrong_idx)
        assert session.score == 0

    def test_completes_after_total_questions(self):
        session = QuizSession()
        for _ in range(TOTAL_QUESTIONS):
            q = session.get_next_question()
            if q:
                session.submit_answer(q, q["correct"])
        assert session.is_complete is True

    def test_no_repeated_questions(self):
        session = QuizSession()
        seen_ids = set()
        for _ in range(TOTAL_QUESTIONS):
            q = session.get_next_question()
            if q:
                assert q["id"] not in seen_ids, "Question repeated in same session"
                seen_ids.add(q["id"])
                session.submit_answer(q, q["correct"])

    def test_reset_clears_state(self):
        session = QuizSession()
        q = session.get_next_question()
        session.submit_answer(q, q["correct"])
        session.reset()

        assert session.score == 0
        assert session.current_difficulty == 1
        assert session.is_complete is False
        assert session.questions_asked == []

    def test_progress_tracking(self):
        session = QuizSession()
        answered, total = session.progress
        assert answered == 0
        assert total == TOTAL_QUESTIONS

        q = session.get_next_question()
        session.submit_answer(q, q["correct"])
        answered, total = session.progress
        assert answered == 1

    def test_final_result_perfect_score(self):
        session = QuizSession()
        for _ in range(TOTAL_QUESTIONS):
            q = session.get_next_question()
            if q:
                session.submit_answer(q, q["correct"])

        result = session.get_final_result("en-IN")
        assert result["score"] == TOTAL_QUESTIONS
        assert result["percentage"] == 100
        assert result["badge_emoji"] == SCORE_BADGES[3]["emoji"]

    def test_final_result_zero_score(self):
        session = QuizSession()
        for _ in range(TOTAL_QUESTIONS):
            q = session.get_next_question()
            if q:
                wrong = (q["correct"] + 1) % 4
                session.submit_answer(q, wrong)

        result = session.get_final_result("en-IN")
        assert result["score"] == 0
        assert result["percentage"] == 0
        assert result["badge_emoji"] == SCORE_BADGES[0]["emoji"]

    def test_hindi_result_title(self):
        session = QuizSession()
        for _ in range(TOTAL_QUESTIONS):
            q = session.get_next_question()
            if q:
                session.submit_answer(q, q["correct"])

        result = session.get_final_result("hi-IN")
        assert result["badge_title"] == SCORE_BADGES[3]["title_hi"]
