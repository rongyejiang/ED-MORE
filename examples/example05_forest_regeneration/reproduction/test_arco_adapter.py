# SPDX-License-Identifier: Apache-2.0
"""Regression checks for hourly ARCO semantics and input rejection."""
import numpy as np
import pytest

from arco_adapter import convert_hourly, read_points


def test_hourly_rain_clips_and_converts_without_differencing():
    values = np.array([-1e-8, 0.001, 0.003, 0.002], dtype="f4")
    spec = {"kind": "accum", "clip_negative": True, "factor": 1000 / 3600}
    result = convert_hourly(values, spec)
    expected = np.array([0, 0.001, 0.003, 0.002], dtype="f4") * np.float32(1000 / 3600)
    np.testing.assert_array_equal(result, expected)
    assert values[0] < 0  # No mutation of source evidence.
    assert result.dtype == np.float32


def test_longwave_does_not_silently_clip():
    values = np.array([-1, 3600, 7200], dtype="f4")
    result = convert_hourly(values, {"kind": "accum", "clip_negative": False, "factor": 1 / 3600})
    np.testing.assert_array_equal(result, values * np.float32(1 / 3600))


def test_instantaneous_fields_keep_values():
    values = np.array([290.1, 291.2], dtype="f4")
    result = convert_hourly(values, {"kind": "instant"})
    np.testing.assert_array_equal(result, values)
    assert not np.shares_memory(values, result)


def test_missing_or_shifted_hours_are_rejected(tmp_path):
    folder = tmp_path / "temperature"
    folder.mkdir()
    np.savez(folder / "point_2003_2022.npz", time=np.array(["2003-01-01T00"], dtype="datetime64[h]"), t2m=[290])
    with pytest.raises(ValueError, match="hours"):
        read_points(tmp_path, ["t2m"])


def test_empty_inputs_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="No point"):
        read_points(tmp_path, ["t2m"])
