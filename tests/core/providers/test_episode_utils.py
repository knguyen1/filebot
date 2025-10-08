# Copyright (c) 2025 knguyen1
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import annotations

import pytest

from filebot.core.models import Episode, MultiEpisode, SeriesInfo
from filebot.core.providers.episode_utils import (
    create_episode,
    episode_numbers_key,
    get_multi_episode_list,
    match_by_absolute,
)


def _ep(num: int, title: str = "") -> Episode:
    return Episode(
        series_name="S",
        season=1,
        episode=num,
        title=title or None,
        absolute=num,
        special_number=None,
        airdate=None,
        id=num,
        series_info=SeriesInfo(id=1, name="S"),
    )


def test_create_episode_single_and_multi() -> None:
    single = create_episode([_ep(1)])
    assert isinstance(single, Episode)
    multi = create_episode([_ep(1), _ep(2)])
    assert isinstance(multi, MultiEpisode)
    assert len(multi.get_episodes()) == 2


def test_create_episode_raises_on_empty() -> None:
    with pytest.raises(ValueError, match="No episodes provided"):
        create_episode([])


@pytest.mark.parametrize(
    "container_factory",
    [list, tuple],
)
def test_create_episode_accepts_sequence_types(container_factory) -> None:
    eps = container_factory([_ep(1), _ep(2)])
    out = create_episode(eps)  # type: ignore[arg-type]
    assert isinstance(out, MultiEpisode)
    assert [e.id for e in out.get_episodes()] == [1, 2]


def test_get_multi_episode_list() -> None:
    e1 = _ep(1)
    e2 = _ep(2)
    assert get_multi_episode_list(e1) == [e1]
    assert get_multi_episode_list(MultiEpisode([e1, e2])) == [e1, e2]


def test_get_multi_episode_list_empty_multi() -> None:
    assert get_multi_episode_list(MultiEpisode([])) == []


@pytest.mark.parametrize(
    ("episode", "expected"),
    [
        (Episode("S", None, None), (0, 0, 0, 0)),
        (Episode("S", 1, None), (1, 0, 0, 0)),
        (Episode("S", 1, 2), (1, 2, 0, 0)),
        (Episode("S", None, None, special_number=3), (0, 0, 3, 0)),
        (Episode("S", None, None, absolute=10), (0, 0, 0, 10)),
        (Episode("S", 2, 1, special_number=None, absolute=5), (2, 1, 0, 5)),
    ],
)
def test_episode_numbers_key_values(
    episode: Episode, expected: tuple[int, int, int, int]
) -> None:
    assert episode_numbers_key(episode) == expected


def test_episode_numbers_key_sorting() -> None:
    items = [
        Episode("S", None, None, special_number=1),
        Episode("S", 1, 2),
        Episode("S", 1, 1),
        Episode("S", None, None, absolute=4),
        Episode("S", 0, 0, absolute=2),
    ]
    out = sorted(items, key=episode_numbers_key)
    # Expect ordering by season, episode, special, absolute (zeros first)
    assert [episode_numbers_key(e) for e in out] == [
        (0, 0, 0, 2),
        (0, 0, 0, 4),
        (0, 0, 1, 0),
        (1, 1, 0, 0),
        (1, 2, 0, 0),
    ]


def test_match_by_absolute_success_and_failure() -> None:
    # success: multi-episode 1-2 mapped from candidates
    src = MultiEpisode([_ep(1), _ep(2)])
    candidates = [_ep(1), _ep(2), Episode("S", None, None, special_number=3)]
    matched = match_by_absolute(src, candidates)
    assert isinstance(matched, MultiEpisode)
    assert [e.absolute for e in matched.get_episodes()] == [1, 2]

    # failure: missing absolute numbers in source
    bad_src = MultiEpisode([
        Episode("S", 1, 1, absolute=None),
        _ep(2),
    ])
    assert match_by_absolute(bad_src, candidates) is None


def test_match_by_absolute_single_episode_success() -> None:
    src = _ep(5)
    candidates = [_ep(5), _ep(6)]
    matched = match_by_absolute(src, candidates)
    assert isinstance(matched, Episode)
    assert matched.absolute == 5


def test_match_by_absolute_ignores_specials_and_requires_all_parts() -> None:
    src = MultiEpisode([_ep(1), _ep(2)])
    # Candidate with matching absolute but marked as special should be ignored
    candidates = [
        Episode("S", None, None, special_number=1, absolute=1),
        _ep(2),
    ]
    assert match_by_absolute(src, candidates) is None


def test_match_by_absolute_handles_empty_candidates() -> None:
    assert match_by_absolute(_ep(1), []) is None


def test_match_by_absolute_duplicate_candidates_do_not_break_selection() -> None:
    src = MultiEpisode([_ep(1), _ep(2)])
    # Include duplicates and out-of-order; per implementation, extra matches cause mismatch -> None
    candidates = [
        _ep(2),
        _ep(1),
        _ep(2),  # duplicate
        Episode("S", None, None, special_number=99, absolute=2),  # ignored special
    ]
    assert match_by_absolute(src, candidates) is None
