import pytest

from src.ml.guardian.claim_router import ClaimRouter
from src.ml.learning.bandit import GuardianBandit
from src.ml.guardian.source_ranker import SourceRanker


@pytest.fixture
def router():
    return ClaimRouter()


@pytest.fixture
def bandit():
    return GuardianBandit()


@pytest.fixture
def ranker():
    return SourceRanker()
