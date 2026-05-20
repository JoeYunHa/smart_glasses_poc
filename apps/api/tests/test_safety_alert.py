"""Regression tests for safety_alert quality gate and color conflict detection.

Covers:
  - _is_safety_response_complete(): partial-success gate and 판독불가 saturation
  - _is_color_conflict(): CV vs text color comparison (vehicle + pedestrian)
  - _extract_vehicle_color_from_text(): section-2 color parsing
  - _extract_pedestrian_color_from_text(): section-1 color parsing
  - _score_via_hough_circles(): Hough Circle signal lamp detection
  - _estimate_signal_scores(): 2-stage scoring (Hough → fallback blob)
  - sanitize_safety_response(): recommendation prefix stripping
"""

from __future__ import annotations

import base64

import cv2
import numpy as np
import pytest

from app.agent.policy import sanitize_safety_response
from app.services.safety_alert import (
    _has_explicit_core_signals,
    _estimate_signal_scores,
    _extract_pedestrian_color_from_text,
    _extract_vehicle_color_from_text,
    _is_cv_signal_strong,
    _is_color_conflict,
    _is_safety_response_complete,
    _score_via_hough_circles,
)


# ── _is_safety_response_complete ─────────────────────────────────────────────

class TestIsResponseComplete:
    def test_accepts_full_korean_response(self):
        response = (
            "1. 보행자 신호: 빨간색\n"
            "2. 차량 신호: 빨간색\n"
            "3. 접근 차량 없음\n"
            "4. 횡단보도 보임\n"
            "5. 위험 없음\n\n"
            "대기하세요."
        )
        assert _is_safety_response_complete(response)

    def test_accepts_two_core_fields_with_recommendation(self):
        """Gate requires ≥2 core fields, not all three."""
        response = (
            "1. 보행자 신호: 빨간색\n"
            "2. 차량 신호: 녹색\n"
            "주의하며 진행하세요."
        )
        assert _is_safety_response_complete(response)

    def test_rejects_missing_recommendation(self):
        response = (
            "1. 보행자 신호: 빨간색\n"
            "2. 차량 신호: 빨간색\n"
            "3. 접근 차량 없음\n"
        )
        assert not _is_safety_response_complete(response)

    def test_rejects_only_one_core_field(self):
        response = "1. 보행자 신호: 빨간색\n\n대기하세요."
        assert not _is_safety_response_complete(response)

    def test_no_false_positive_vehicle_signal_as_approaching(self):
        """'vehicle' in 'vehicle signal' must NOT satisfy has_approaching_vehicle.

        Before the fix, has_approaching_vehicle matched ('vehicle' in text), so a
        response with only field 1 (pedestrian) and field 2 (vehicle signal mentioning
        'vehicle') would give core_hits=2 and pass — even though field 3 was absent.
        """
        response = (
            "1. Pedestrian signal: 판독 불가\n"
            "2. Vehicle signal: green\n"
            "\n주의하며 진행하세요."
        )
        # has_ped=True (pedestrian), has_vehicle_signal=False (no 차량+신호, no traffic light),
        # has_approaching_vehicle must be False (no 접근, no approach, no section-3 header)
        # → core_hits < 2 → should REJECT
        assert not _is_safety_response_complete(response)

    def test_section3_header_counts_as_approaching_vehicle(self):
        """A section-3 header with any content satisfies the approaching-vehicle field."""
        response = (
            "1. 보행자 신호: 적색\n"
            "2. 차량 신호: 적색\n"
            "3. 판독 불가\n\n"
            "대기하세요."
        )
        assert _is_safety_response_complete(response)

    def test_approach_keyword_satisfies_approaching_vehicle(self):
        response = (
            "Pedestrian signal: red hand\n"
            "Approaching vehicles: two cars approach the crosswalk.\n"
            "\n대기하세요."
        )
        assert _is_safety_response_complete(response)

    def test_empty_response_rejected(self):
        assert not _is_safety_response_complete("")

    def test_recommendation_variants(self):
        base = "1. 보행자: 적색\n2. 차량 신호: 적색\n3. 접근 없음\n\n"
        for rec in ("대기하세요.", "주의하며 진행하세요.", "건너기 전 주변을 직접 확인하세요.", "wait.", "caution"):
            assert _is_safety_response_complete(base + rec), f"Recommendation not recognized: {rec!r}"

    def test_rejects_판독불가_saturation(self):
        """eval.jsonl regression: text_only produced 4 판독불가 fields → must be rejected.

        request_id=f4cd22b9 responded with ped=green and 4 unreadable fields while
        the actual signal was red.  The 판독불가 gate forces an image retry.
        """
        response = (
            "1. 보행 신호 상태/색상: 녹색\n"
            "2. 차량 신호 상태/색상: 판독 불가\n"
            "3. 접근하는 차량: 판독 불가\n"
            "4. 횡단보도 가시성 및 장애물: 판독 불가\n"
            "5. 기타 위험 요소: 판독 불가\n\n"
            "주의하며 진행하세요."
        )
        assert not _is_safety_response_complete(response)

    def test_three_판독불가_still_passes(self):
        """Exactly 3 unreadable fields is a legitimate hard-scene response — must pass."""
        response = (
            "1. 보행자 신호: 빨간색\n"
            "2. 차량 신호: 판독 불가\n"
            "3. 접근 차량: 판독 불가\n"
            "4. 횡단보도: 판독 불가\n"
            "5. 기타: 이상 없음\n\n"
            "대기하세요."
        )
        assert _is_safety_response_complete(response)


# ── _extract_vehicle_color_from_text ─────────────────────────────────────────

class TestExtractVehicleColor:
    def test_section2_red(self):
        response = "1. 보행자: 적색\n2. 차량 신호: 빨간색\n3. 접근 없음"
        assert _extract_vehicle_color_from_text(response) == "red"

    def test_section2_green(self):
        response = "1. 보행자: 녹색\n2. 차량 신호: 초록색\n3. 없음"
        assert _extract_vehicle_color_from_text(response) == "green"

    def test_section2_yellow(self):
        response = "1. 보행자: 판독 불가\n2. 차량 신호: 황색\n3. 없음"
        assert _extract_vehicle_color_from_text(response) == "yellow"

    def test_ambiguous_returns_unknown(self):
        response = "신호 정보 없음\n판독 불가"
        assert _extract_vehicle_color_from_text(response) == "unknown"

    def test_multiple_colors_returns_unknown(self):
        """When red AND green appear in the vehicle section, result is ambiguous."""
        response = "2. 차량 신호: 빨간색과 초록색 혼재"
        assert _extract_vehicle_color_from_text(response) == "unknown"


# ── _extract_pedestrian_color_from_text ───────────────────────────────────────

class TestExtractPedestrianColor:
    def test_section1_red(self):
        response = "1. 보행자 신호: 빨간색\n2. 차량 신호: 판독 불가"
        assert _extract_pedestrian_color_from_text(response) == "red"

    def test_section1_green(self):
        response = "1. 보행자 신호: 녹색\n2. 차량 신호: 빨간색"
        assert _extract_pedestrian_color_from_text(response) == "green"

    def test_파란불_maps_to_green(self):
        """파란불 is a common Korean term for the pedestrian walk (green) signal."""
        response = "1. 보행자 신호: 파란불\n2. 차량 신호: 빨간색"
        assert _extract_pedestrian_color_from_text(response) == "green"

    def test_unreadable_returns_unknown(self):
        response = "1. 보행자 신호: 판독 불가\n2. 차량 신호: 빨간색"
        assert _extract_pedestrian_color_from_text(response) == "unknown"

    def test_no_section1_returns_unknown(self):
        response = "차량 신호: 빨간색\n접근 차량 없음\n대기하세요."
        assert _extract_pedestrian_color_from_text(response) == "unknown"


# ── _is_color_conflict ───────────────────────────────────────────────────────

def _make_red_frame_b64(size: int = 120) -> str:
    """Create a synthetic frame with a bright red circle in the upper region."""
    frame = np.zeros((size, size, 3), dtype=np.uint8)
    # Draw a saturated red circle in the upper-centre (signal area)
    cv2.circle(frame, (size // 2, size // 4), size // 8, (0, 0, 220), -1)
    ok, enc = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    assert ok
    return base64.b64encode(enc.tobytes()).decode()


class TestIsColorConflict:
    def test_no_image_returns_false(self):
        response = "2. 차량 신호: 초록색\n3. 접근 없음\n\n주의하며 진행하세요."
        assert not _is_color_conflict(response, image_b64=None)

    def test_invalid_b64_returns_false(self):
        assert not _is_color_conflict("차량 신호: 초록색", image_b64="!!!invalid!!!")

    def test_returns_bool(self):
        result = _is_color_conflict("차량 신호: 초록색", image_b64=None)
        assert isinstance(result, bool)

    def test_pedestrian_green_with_red_cv_and_unknown_vehicle_is_not_conflict(self):
        """Vehicle color unknown is conservative-safe; no conflict should be forced."""
        response = (
            "1. 보행자 신호: 녹색\n"
            "2. 차량 신호: 판독 불가\n"
            "3. 접근 차량: 판독 불가\n\n"
            "주의하며 진행하세요."
        )
        red_b64 = _make_red_frame_b64()
        assert not _is_color_conflict(response, image_b64=red_b64)


# ── _score_via_hough_circles / _estimate_signal_scores ───────────────────────

class TestHoughCircleScoring:
    def _red_circle_frame(self, size: int = 200) -> np.ndarray:
        frame = np.zeros((size, size, 3), dtype=np.uint8)
        cv2.circle(frame, (size // 2, size // 4), size // 10, (0, 0, 220), -1)
        return frame

    def _green_circle_frame(self, size: int = 200) -> np.ndarray:
        frame = np.zeros((size, size, 3), dtype=np.uint8)
        cv2.circle(frame, (size // 2, size // 4), size // 10, (0, 200, 0), -1)
        return frame

    def _blank_frame(self, size: int = 200) -> np.ndarray:
        return np.zeros((size, size, 3), dtype=np.uint8)

    def test_returns_none_for_blank_frame(self):
        result = _score_via_hough_circles(self._blank_frame())
        # A blank frame has no circles — Hough should return None.
        assert result is None

    def test_red_circle_detected(self):
        upper = self._red_circle_frame()
        scores = _score_via_hough_circles(upper)
        if scores is not None:
            # When circles ARE detected, red should dominate.
            assert scores["red"] >= scores["green"]

    def test_estimate_scores_returns_dict(self):
        frame = self._red_circle_frame()
        scores = _estimate_signal_scores(frame)
        assert set(scores.keys()) == {"red", "yellow", "green"}
        assert all(v >= 0.0 for v in scores.values())

    def test_estimate_scores_red_dominant_on_red_circle(self):
        frame = self._red_circle_frame(size=300)
        scores = _estimate_signal_scores(frame)
        # Either Hough or blob fallback — red should beat green.
        assert scores["red"] >= scores["green"]

    def test_estimate_scores_green_dominant_on_green_circle(self):
        frame = self._green_circle_frame(size=300)
        scores = _estimate_signal_scores(frame)
        assert scores["green"] >= scores["red"]

    def test_tiny_frame_returns_zeros(self):
        frame = np.zeros((4, 4, 3), dtype=np.uint8)
        scores = _estimate_signal_scores(frame)
        assert scores == {"red": 0.0, "yellow": 0.0, "green": 0.0}


# ── sanitize_safety_response: recommendation prefix stripping ─────────────────

class TestSanitizeSafetyResponse:
    def test_strips_주요추천_prefix(self):
        """eval.jsonl regression: LLM output '주요 추천: 주의하며 진행하세요.' must be cleaned."""
        result = sanitize_safety_response("1. 보행자: 빨간색\n\n주요 추천: 주의하며 진행하세요.")
        assert "주요 추천:" not in result
        assert "주의하며 진행하세요." in result

    def test_strips_최종추천_prefix(self):
        result = sanitize_safety_response("대기 필요.\n\n최종 추천: 대기하세요.")
        assert "최종 추천:" not in result
        assert "대기하세요." in result

    def test_preserves_overconfident_phrase_replacement(self):
        result = sanitize_safety_response("건너셔도 됩니다.")
        assert "건너셔도 됩니다" not in result

    def test_no_prefix_unchanged(self):
        clean = "1. 보행자: 빨간색\n\n대기하세요."
        assert sanitize_safety_response(clean) == clean


# ── semantic_extractor: safety mode signal_area_colors ───────────────────────

class TestSemanticExtractorSafetyMode:
    def test_safety_mode_populates_signal_area_colors(self):
        from app.perception.semantic_extractor import SemanticPayload, extract_semantic

        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        # Paint upper region red (signal area)
        cv2.circle(frame, (100, 40), 20, (0, 0, 200), -1)

        payload = extract_semantic(frame, mode="safety")
        assert isinstance(payload.signal_area_colors, list)
        # Red circle in upper region should produce "red" in signal_area_colors.
        assert "red" in payload.signal_area_colors

    def test_general_mode_has_no_signal_area_colors(self):
        from app.perception.semantic_extractor import extract_semantic

        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        payload = extract_semantic(frame, mode="general")
        assert payload.signal_area_colors == []

    def test_build_semantic_prompt_includes_signal_area(self):
        from app.perception.semantic_extractor import SemanticPayload, build_semantic_prompt

        payload = SemanticPayload(signal_area_colors=["red"], dominant_colors=["red", "green"])
        prompt = build_semantic_prompt([payload], "지금 건너도 돼?")
        assert "signal_area=red" in prompt
        # signal_area must appear before colors= so LLM prioritises it.
        assert prompt.index("signal_area=") < prompt.index("colors=")


class TestSafetyVehicleOnlyConflictAndCvStrength:
    def test_vehicle_only_conflict_gate_allows_ped_green_vehicle_red(self):
        response = (
            "1. Pedestrian signal: green\n"
            "2. Vehicle signal: red\n"
            "3. Approaching vehicles: none\n\n"
            "Wait."
        )
        red_b64 = _make_red_frame_b64()
        assert not _is_color_conflict(response, image_b64=red_b64)

    def test_cv_signal_strong_true_on_clear_red_signal(self):
        red_b64 = _make_red_frame_b64()
        assert _is_cv_signal_strong(red_b64, min_conf=0.58, min_visibility=0.0)


class TestCoreSignalQuality:
    def test_explicit_core_signals_true(self):
        response = (
            "1. Pedestrian signal: red\n"
            "2. Vehicle signal: green\n"
            "3. Approaching vehicles: none\n\n"
            "Wait."
        )
        assert _has_explicit_core_signals(response)

    def test_explicit_core_signals_false_on_estimated(self):
        response = (
            "1. 보행자 신호: 빨간색 계열 추정(정지 권고)\n"
            "2. 차량 신호: yellow 계열 감지(추정)\n"
            "3. 접근 차량: 판단 어려움(직접 확인 필요)\n\n"
            "대기하세요."
        )
        assert not _has_explicit_core_signals(response)
