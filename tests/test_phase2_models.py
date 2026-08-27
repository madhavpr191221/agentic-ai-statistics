from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mcp_traffic_analysis.analysis.phase2_models import fit_phase2_models


@pytest.mark.filterwarnings("ignore:The MLE may be on the boundary of the parameter space")
def test_primary_factorial_model_recovers_known_signal(tmp_path: Path) -> None:
    runs: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []
    order = 0
    for transport in ("in_memory", "stdio"):
        for payload in (64, 1024, 16384, 65536):
            for service in (0, 20, 100):
                for concurrency in (1, 4):
                    for _replicate in (1, 2):
                        order += 1
                        run_id = f"run-{order}"
                        base = (
                            1
                            + (transport == "stdio") * 0.4
                            + np.log2(payload) * 0.03
                            + service * 0.01
                            + concurrency * 0.02
                        )
                        runs.append({"run_id": run_id, "execution_order": order})
                        for call_index in range(2):
                            calls.append(
                                {
                                    "run_id": run_id,
                                    "call_index": call_index,
                                    "outcome": "success",
                                    "client_roundtrip_ms": base * (1 + call_index * 0.001),
                                    "transport": transport,
                                    "payload_target_bytes": payload,
                                    "service_time_ms": service,
                                    "concurrency": concurrency,
                                    "is_first_call": call_index == 0,
                                    "total_frame_bytes": payload * 2
                                    if transport == "stdio"
                                    else None,
                                }
                            )
    result = fit_phase2_models(
        tmp_path,
        pd.DataFrame(runs),
        pd.DataFrame(calls),
        bootstrap_iterations=20,
        bootstrap_seed=7,
    )
    assert result["primary_model"]["n_runs"] == 96
    # The fixed-effect structure deliberately omits a higher-order interaction
    # present in this synthetic signal, so strong recovery rather than a
    # mathematically exact fit is the appropriate contract.
    assert result["primary_model"]["r_squared"] > 0.98
    assert len(result["condition_summaries"]) == 48
