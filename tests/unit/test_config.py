from backend.core.config import Settings
from backend.solvers.base import OptimizationProblem


def test_settings_defaults():
    settings = Settings()
    assert settings.API_PORT == 8000
    assert settings.DEFAULT_K_COVERAGE == 2
    assert "sqlite" in settings.DATABASE_URL


def test_optimization_problem_dataclass():
    problem = OptimizationProblem(
        num_targets=2,
        num_waypoints=3,
        sensing_matrix=[[1, 1, 0], [0, 1, 1]],
        k_coverage=1,
    )
    assert problem.num_targets == 2
    assert problem.num_waypoints == 3
    assert problem.sensing_matrix[0][0] == 1
    assert problem.k_coverage == 1

