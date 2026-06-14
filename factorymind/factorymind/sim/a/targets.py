"""Named targets → pose labels (precomputed lookup; MuJoCo uses joint goals later)."""

TARGET_POSES: dict[str, str] = {
    "home": "home",
    "bin_a": "above_bin_a",
    "bin_b": "above_bin_b",
    "station_1": "above_station_1",
    "station_2": "above_station_2",
    "part_1": "above_part_1",
    "part_2": "above_part_2",
    "part_3": "above_part_3",
}
