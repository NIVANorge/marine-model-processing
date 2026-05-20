import numpy as np
import pytest

from waves.classify import CLASSES, SWM_BINS, classify_swm_values


class TestSWMBins:
    def test_bin_count(self):
        assert len(SWM_BINS) == 9, "9 breakpoints → 10 classes"

    def test_bins_are_strictly_increasing(self):
        assert all(SWM_BINS[i] < SWM_BINS[i + 1] for i in range(len(SWM_BINS) - 1))


class TestClassesTable:
    def test_ten_rows(self):
        assert len(CLASSES) == 10

    def test_class_int_range(self):
        assert list(CLASSES["class_int"]) == list(range(1, 11))

    def test_no_null_names(self):
        assert CLASSES["navn_no"].notna().all()
        assert CLASSES["navn_en"].notna().all()


class TestClassifySWMValues:
    # Each entry: (swm_value, expected_class)
    boundary_cases = [
        (0, 0),            # nodata → 0
        (1, 1),            # ≤ 1200 → class 1 (still water)
        (1_200, 1),
        (1_201, 2),        # > 1200 → class 2
        (4_000, 2),
        (4_001, 3),
        (10_000, 3),
        (10_001, 4),
        (50_000, 4),
        (50_001, 5),
        (100_000, 5),
        (100_001, 6),
        (500_000, 6),
        (500_001, 7),
        (1_000_000, 7),
        (1_000_001, 8),
        (2_000_000, 8),
        (2_000_001, 9),
        (4_000_000, 9),
        (4_000_001, 10),
        (5_000_000, 10),   # above max → class 10
    ]

    @pytest.mark.parametrize("swm,expected", boundary_cases)
    def test_boundary(self, swm, expected):
        data = np.array([[swm]], dtype=np.int32)
        result = classify_swm_values(data, nodata=0)
        assert result[0, 0] == expected, f"SWM={swm} should → class {expected}, got {result[0,0]}"

    def test_nodata_preserved(self):
        data = np.array([[0, 500, 0]], dtype=np.int32)
        result = classify_swm_values(data, nodata=0)
        assert result[0, 0] == 0
        assert result[0, 2] == 0
        assert result[0, 1] == 1

    def test_output_dtype_is_uint8(self):
        data = np.array([[100_000]], dtype=np.int32)
        result = classify_swm_values(data)
        assert result.dtype == np.uint8

    def test_output_shape_matches_input(self):
        data = np.zeros((64, 128), dtype=np.int32)
        result = classify_swm_values(data)
        assert result.shape == data.shape

    def test_all_classes_reachable(self):
        representative = [100, 1_201, 4_001, 10_001, 50_001, 100_001, 500_001, 1_000_001, 2_000_001, 4_000_001]
        data = np.array([representative], dtype=np.int32)
        result = classify_swm_values(data)
        assert set(result.flat) == set(range(1, 11))
