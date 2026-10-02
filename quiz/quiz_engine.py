"""
quiz/quiz_engine.py
────────────────────
Adaptive quiz engine. Manages quiz state and difficulty escalation.

Adaptive Logic:
  - Start at difficulty 1
  - Correct answer → move to next difficulty level (max 3)
  - Wrong answer   → stay at same level, show explanation, proceed
  - 3 questions total, then show score badge

Score Badges (for IIT Mandi Track D — adaptive learning):
  3/3 correct → 🏆 Fraud Defender
  2/3 correct → 🥈 Alert Investor
  1/3 correct → 🥉 Learning Investor
  0/3 correct → 📚 Awareness Needed
"""

import random
import logging
from quiz.questions import QUESTIONS, get_questions_by_difficulty

logger = logging.getLogger(__name__)

TOTAL_QUESTIONS = 3

SCORE_BADGES = {
    3: {"emoji": "🏆", "title_en": "Fraud Defender",    "title_hi": "धोखाधड़ी रक्षक",
        "desc_en":  "Outstanding! You can identify investment frauds with expert precision.",
        "desc_hi":  "शानदार! आप विशेषज्ञ सटीकता के साथ निवेश धोखाधड़ी की पहचान कर सकते हैं।"},
    2: {"emoji": "🥈", "title_en": "Alert Investor",    "title_hi": "सतर्क निवेशक",
        "desc_en":  "Well done! You have good fraud awareness. Keep learning!",
        "desc_hi":  "शाबाश! आपमें अच्छी धोखाधड़ी जागरूकता है। सीखते रहें!"},
    1: {"emoji": "🥉", "title_en": "Learning Investor",  "title_hi": "सीखने वाला निवेशक",
        "desc_en":  "Good start! Review the explanations to sharpen your fraud-detection skills.",
        "desc_hi":  "अच्छी शुरुआत! अपनी धोखाधड़ी-पहचान क्षमता को तेज करने के लिए स्पष्टीकरण पढ़ें।"},
    0: {"emoji": "📚", "title_en": "Awareness Needed",  "title_hi": "जागरूकता आवश्यक",
        "desc_en":  "Don't worry — learning now protects you from fraud later. Review all explanations!",
        "desc_hi":  "चिंता न करें — अभी सीखना आपको भविष्य में धोखाधड़ी से बचाएगा!"},
}


class QuizSession:
    """
    Manages state for a single user's quiz session.

    Attributes:
        current_difficulty (int):   Current difficulty level (1–3)
        questions_asked    (list):  Question IDs already shown
        answers_given      (list):  List of {"question_id", "correct", "chosen_index"}
        score              (int):   Running count of correct answers
        is_complete        (bool):  True when 3 questions have been answered
    """

    def __init__(self):
        self.current_difficulty: int = 1
        self.questions_asked: list[str] = []
        self.answers_given: list[dict] = []
        self.score: int = 0
        self.is_complete: bool = False

    def get_next_question(self) -> dict | None:
        """
        Select the next question based on current difficulty.
        Avoids repeating already-shown questions.

        Returns:
            Question dict or None if all questions at this level exhausted.
        """
        if self.is_complete:
            return None

        available = [
            q for q in get_questions_by_difficulty(self.current_difficulty)
            if q["id"] not in self.questions_asked
        ]

        if not available:
            # Fallback: pull from any difficulty not yet asked
            available = [
                q for q in QUESTIONS
                if q["id"] not in self.questions_asked
            ]

        if not available:
            self.is_complete = True
            return None

        question = random.choice(available)
        logger.debug(f"Next question: {question['id']} (difficulty {self.current_difficulty})")
        return question

    def submit_answer(self, question: dict, chosen_index: int) -> dict:
        """
        Process a submitted answer and update quiz state.

        Args:
            question:      The question dict that was answered.
            chosen_index:  0-indexed option the user selected.

        Returns:
            Result dict: {"is_correct": bool, "correct_index": int, ...}
        """
        is_correct = (chosen_index == question["correct"])
        self.questions_asked.append(question["id"])
        self.answers_given.append({
            "question_id":   question["id"],
            "correct":       is_correct,
            "chosen_index":  chosen_index,
            "correct_index": question["correct"],
            "difficulty":    question["difficulty"],
        })

        if is_correct:
            self.score += 1
            # Adaptive: escalate difficulty
            self.current_difficulty = min(self.current_difficulty + 1, 3)
            logger.debug(f"Correct! New difficulty: {self.current_difficulty}")
        else:
            # Wrong: stay at same difficulty (don't go below 1)
            logger.debug(f"Wrong. Staying at difficulty: {self.current_difficulty}")

        # Check completion
        if len(self.questions_asked) >= TOTAL_QUESTIONS:
            self.is_complete = True

        return {
            "is_correct":    is_correct,
            "correct_index": question["correct"],
            "explanation_en": question.get("explanation_en", ""),
            "explanation_hi": question.get("explanation_hi", ""),
            "source":        question.get("source", ""),
            "fraud_type":    question.get("fraud_type", ""),
        }

    def get_final_result(self, lang_code: str = "hi-IN") -> dict:
        """
        Compute the final quiz result and badge.

        Args:
            lang_code: BCP-47 language code for localized output.

        Returns:
            Result dict with score, badge, and performance breakdown.
        """
        badge = SCORE_BADGES.get(self.score, SCORE_BADGES[0])
        is_hindi = lang_code.startswith("hi")

        return {
            "score":        self.score,
            "total":        TOTAL_QUESTIONS,
            "percentage":   round((self.score / TOTAL_QUESTIONS) * 100),
            "badge_emoji":  badge["emoji"],
            "badge_title":  badge["title_hi"] if is_hindi else badge["title_en"],
            "badge_desc":   badge["desc_hi"]  if is_hindi else badge["desc_en"],
            "answers":      self.answers_given,
            "fraud_types_missed": [
                a.get("fraud_type", "unknown")
                for a in self.answers_given
                if not a["correct"]
            ],
        }

    def reset(self):
        """Reset the session for a new quiz attempt."""
        self.__init__()
        logger.debug("Quiz session reset")

    @property
    def progress(self) -> tuple[int, int]:
        """Return (questions_answered, total_questions)."""
        return len(self.questions_asked), TOTAL_QUESTIONS
