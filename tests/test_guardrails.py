"""
tests/test_guardrails.py
─────────────────────────
Unit tests for the safety filter module.
Verifies that stock tip queries are blocked and safe queries pass through.
"""

import pytest
from guardrails.safety_filter import (
    check_query,
    check_answer,
    get_refusal_message,
    get_fraud_alert_message,
)


class TestCheckQuery:
    """Tests for Layer 1 pre-LLM query safety check."""

    # ── Queries that MUST be blocked ─────────────────────────────────────────

    def test_blocks_buy_stock(self):
        is_blocked, _ = check_query("Should I buy Reliance stock now?")
        assert is_blocked is True

    def test_blocks_sell_stock(self):
        is_blocked, _ = check_query("When should I sell my HDFC shares?")
        assert is_blocked is True

    def test_blocks_price_target(self):
        is_blocked, _ = check_query("What is the price target for Infosys?")
        assert is_blocked is True

    def test_blocks_guaranteed_return(self):
        is_blocked, _ = check_query("Give me a scheme with 30% guaranteed return")
        assert is_blocked is True

    def test_blocks_guaranteed_return_percentage(self):
        is_blocked, _ = check_query("Is there a 50% guaranteed return fund?")
        assert is_blocked is True

    def test_blocks_stock_tip(self):
        is_blocked, _ = check_query("Give me a stock tip for tomorrow")
        assert is_blocked is True

    def test_blocks_hindi_transliteration(self):
        is_blocked, _ = check_query("konsa stock kharidna chahiye?")
        assert is_blocked is True

    # ── Queries that MUST pass through ───────────────────────────────────────

    def test_allows_mutual_fund_query(self):
        is_blocked, _ = check_query("What is a mutual fund?")
        assert is_blocked is False

    def test_allows_sebi_query(self):
        is_blocked, _ = check_query("What does SEBI do to protect investors?")
        assert is_blocked is False

    def test_allows_whatsapp_fraud_query(self):
        is_blocked, _ = check_query("Is this WhatsApp investment group safe?")
        assert is_blocked is False

    def test_allows_sip_query(self):
        is_blocked, _ = check_query("How does a SIP work?")
        assert is_blocked is False

    def test_allows_fraud_awareness_query(self):
        is_blocked, _ = check_query("What are signs of a Ponzi scheme?")
        assert is_blocked is False

    def test_allows_empty_string(self):
        is_blocked, _ = check_query("")
        assert is_blocked is False


class TestCheckAnswer:
    """Tests for Layer 2 post-LLM answer safety check."""

    def test_flags_buy_advice_in_answer(self):
        answer = "You should buy Tata Steel stock right now for best gains."
        is_violating, _ = check_answer(answer)
        assert is_violating is True

    def test_flags_guaranteed_return_in_answer(self):
        answer = "This scheme offers guaranteed returns of 25% per year."
        is_violating, _ = check_answer(answer)
        assert is_violating is True

    def test_passes_clean_educational_answer(self):
        answer = (
            "A mutual fund pools money from many investors to invest in "
            "stocks, bonds or other securities. [Source: SEBI Mutual Funds Guide, Pg 3]"
        )
        is_violating, _ = check_answer(answer)
        assert is_violating is False

    def test_passes_refusal_message(self):
        answer = "I cannot provide stock tips per SEBI guidelines."
        is_violating, _ = check_answer(answer)
        assert is_violating is False


class TestRefusalMessages:
    """Tests for refusal and fraud alert message generation."""

    def test_hindi_refusal_contains_sebi_helpline(self):
        msg = get_refusal_message("hi-IN")
        assert "1800-266-7575" in msg

    def test_english_refusal_contains_sebi_helpline(self):
        msg = get_refusal_message("en-IN")
        assert "1800-266-7575" in msg

    def test_hindi_refusal_is_in_hindi(self):
        msg = get_refusal_message("hi-IN")
        # Must contain Devanagari characters
        assert any('\u0900' <= c <= '\u097F' for c in msg)

    def test_fraud_alert_contains_cybercrime(self):
        msg = get_fraud_alert_message("en-IN")
        assert "cybercrime.gov.in" in msg

    def test_fraud_alert_hindi_contains_cybercrime(self):
        msg = get_fraud_alert_message("hi-IN")
        assert "cybercrime.gov.in" in msg
