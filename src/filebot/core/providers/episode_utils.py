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

"""
Episode utilities: multi-episode composition and cross-provider matching.

This module provides helpers similar to Java's EpisodeUtilities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from filebot.core.models import Episode, MultiEpisode

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


def create_episode(episodes: Sequence[Episode]) -> Episode | MultiEpisode:
    """Return a single Episode or a MultiEpisode grouping.

    Parameters
    ----------
    episodes:
        One or more episodes referring to the same series.
    """
    if not episodes:
        msg = "No episodes provided"
        raise ValueError(msg)
    if len(episodes) == 1:
        return episodes[0]
    return MultiEpisode(list(episodes))


def get_multi_episode_list(e: Episode | MultiEpisode) -> list[Episode]:
    """Return the underlying episodes for a single or grouped value.

    Parameters
    ----------
    e:
        Either a single `Episode` or a `MultiEpisode` grouping.

    Returns
    -------
    list[Episode]
        A list containing the single episode or the grouped episodes.
    """
    return e.get_episodes() if isinstance(e, MultiEpisode) else [e]


def episode_numbers_key(e: Episode) -> tuple[int, int, int, int]:
    """Return a sortable key based on common episode numbering fields.

    Parameters
    ----------
    e:
        Episode whose numbers should be used for sorting.

    Returns
    -------
    tuple[int, int, int, int]
        Tuple of (season, episode, special, absolute) with missing values
        normalized to zero for stable ordering.
    """
    season = e.season if e.season is not None else 0
    episode = e.episode if e.episode is not None else 0
    special = e.special_number if e.special_number is not None else 0
    absolute = e.absolute if e.absolute is not None else 0
    return (season, episode, special, absolute)


def match_by_absolute(
    source: Episode | MultiEpisode,
    candidates: Iterable[Episode],
) -> Episode | MultiEpisode | None:
    """Match episodes by absolute numbering across providers.

    Parameters
    ----------
    source:
        Episode or MultiEpisode with absolute numbers populated.
    candidates:
        Iterable of episodes from another provider to match.

    Returns
    -------
    Episode | MultiEpisode | None
        Matched single or multi-episode; None if not all parts matched.
    """
    parts = get_multi_episode_list(source)
    abs_set = {e.absolute for e in parts if e.absolute is not None}
    if not abs_set or len(abs_set) != len(parts):
        return None

    found: list[Episode] = [
        e for e in candidates if e.special_number is None and e.absolute in abs_set
    ]

    if len(found) != len(parts):
        return None

    found.sort(key=episode_numbers_key)
    return create_episode(found)
