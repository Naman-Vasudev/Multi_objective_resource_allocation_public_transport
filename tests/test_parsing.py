"""Pure parser tests (required by the Stage 1 definition of done)."""
import datetime as dt

import pytest

from src import data as D
from src import params as P

T = dt.time


@pytest.mark.parametrize("text, lo, hi", [("20-25", 20, 25), ("15-30", 15, 30), ("20", 20, 20),
                                          ("10-15", 10, 15), ("50-55", 50, 55), ("20–25", 20, 25)])
def test_headway_range(text, lo, hi):
    assert D.parse_headway_range(text) == (lo, hi)


@pytest.mark.parametrize("bad", ["", "abc", "25-20", "0", "20-"])
def test_headway_range_rejects_bad(bad):
    with pytest.raises(ValueError):
        D.parse_headway_range(bad)


def test_headway_to_frequency_uses_longest_headway_for_f_min():
    lo, hi = D.parse_headway_range("15-30")
    f_max, f_min = P.headway_min_to_freq_per_h(lo), P.headway_min_to_freq_per_h(hi)
    assert (f_min, f_max) == (2.0, 4.0)          # dep/h
    lo, hi = D.parse_headway_range("20-25")
    assert P.headway_min_to_freq_per_h(hi) == pytest.approx(2.4)
    assert P.headway_min_to_freq_per_h(lo) == pytest.approx(3.0)


def test_unit_round_trip():
    for h in (10, 15, 20, 25, 30, 45, 60, 80, 90):
        assert P.freq_per_h_to_headway_min(P.headway_min_to_freq_per_h(h)) == pytest.approx(h)
    with pytest.raises(ValueError):
        P.headway_min_to_freq_per_h(0)


def test_two_window_operating_hours():
    assert D.parse_operating_hours("06.10-17.20 / 07.30-18.40") == [(T(6, 10), T(17, 20)), (T(7, 30), T(18, 40))]


def test_single_window_colon_and_note_variants():
    assert D.parse_operating_hours("10:10-15.50") == [(T(10, 10), T(15, 50))]
    assert D.parse_operating_hours("05.00-20.00 / 06.20-21.20 (fixed departures)") == \
        [(T(5, 0), T(20, 0)), (T(6, 20), T(21, 20))]


def test_overnight_window_and_span():
    [(a, b)] = D.parse_operating_hours("22.00-04.40")
    assert (a, b) == (T(22, 0), T(4, 40))
    assert D.span_hours(a, b) == pytest.approx(6 + 40 / 60)   # hours, wraps past midnight
    assert D.span_hours(T(6, 10), T(18, 40)) == pytest.approx(12.5)


def test_route_number_25_25A_kept_intact():
    assert D.parse_route_list("1, 101, 25/25A, 2A") == ["1", "101", "25/25A", "2A"]
    assert D.normalize_route_no(" 25/25A ") == "25/25A"


def test_route_number_numeric_becomes_string():
    assert D.normalize_route_no(1) == "1"
    assert D.normalize_route_no(1.0) == "1"
    assert D.parse_route_list(None) == []
