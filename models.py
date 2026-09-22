"""Pydantic 모델 정의 - 요청/응답 데이터 형식"""

from pydantic import BaseModel
from typing import Optional, List


# === 리뷰 관련 모델 ===

class ReviewCreate(BaseModel):
    """리뷰 생성 요청"""
    content: str
    game_name: Optional[str] = None


class ReviewResponse(BaseModel):
    """리뷰 응답"""
    id: int
    content: str
    game_name: Optional[str]
    created_at: str


# === 분석 관련 모델 ===

class AnalyzeRequest(BaseModel):
    """분석 요청"""
    review_id: int


class AnalysisResponse(BaseModel):
    """분석 결과 응답"""
    review_id: int
    sentiment: str  # 긍정, 부정, 중립
    keywords: List[str]
    confidence: float
    analyzed_at: str


# === 통계 관련 모델 ===

class StatsResponse(BaseModel):
    """통계 응답"""
    total_reviews: int
    analyzed_count: int
    sentiment_distribution: dict  # {"긍정": 10, "부정": 5, "중립": 3}
