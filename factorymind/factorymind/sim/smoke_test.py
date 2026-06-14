"""Smoke test: mock cell + oracle policy, no LLM required."""

from factorymind.sim.mock_cell import MockCellEnv
from factorymind.sim.oracle import run_oracle_episode


def main() -> None:
    env = MockCellEnv(num_robots=2, seed=0)
    final = run_oracle_episode(env)
    assert final["done"], f"Oracle failed to complete task: {final}"
    placed = sum(1 for p in final["parts"] if p["at"] == "station_1")
    print(f"OK — task complete in {final['step']} steps, {placed} parts at station_1")
    print(f"Final state: {final}")


if __name__ == "__main__":
    main()
