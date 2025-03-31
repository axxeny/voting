"""Proportional Approval Voting (NP-complete).

Supports multiple apportionment methods.
"""


from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import chain, combinations
from typing import Literal, Self

import pandas as pd

Candidate = str
type Ballot = set[Candidate]


class ApportionmentMethod(ABC):
    """Abstract class for apportionment methods (d'Hondt, Sainte-Laguë etc.)."""

    @classmethod
    @abstractmethod
    def dv(cls, index: int) -> float:
        """(0) -> 0., (1) -> 1., (2) -> .5, (3) -> .3333, ... for d'Hondt method."""
        ...

    @classmethod
    def v(cls, index: int) -> float:
        """(0) -> 0., (1) -> 1., (2) -> 1.5, (3) -> 1.8333, ... for d'Hondt method."""
        if index < 0:
            raise ValueError
        if index == 0:
            return 0
        return sum(cls.dv(i) for i in range(1, index + 1))

    @classmethod
    def from_name(
        cls, name: Literal[
            "d_hondt",
            "sainte_lague",
            "sainte_lague_1_2",
            "sainte_lague_1_4",
        ],
    ) -> Self:
        """Apportionment method factory."""
        return {
            "sainte_lague": SainteLagueApportionmentMethod,
            "sainte_lague_1_2": SainteLague12ApportionmentMethod,
            "sainte_lague_1_4": SainteLague14ApportionmentMethod,
        }[name]

class SainteLagueApportionmentMethod(ApportionmentMethod):
    """Sainte-Laguë Apportionment Method."""

    @classmethod
    def dv(cls, index: int) -> float:
        """(0) -> 0., (1) -> 1., (2) -> .3333, (3) -> .2, ..."""
        if index < 0:
            raise ValueError
        if index == 0:
            return 0
        return 1. / (-1 + 2 * index)



class SainteLague12ApportionmentMethod(ApportionmentMethod):
    """Modified Sainte-Laguë Apportionment Method (first dv is 1.2)."""

    @classmethod
    def dv(cls, index: int) -> float:
        """(0) -> 0., (1) -> .8333, (2) -> .3333, (3) -> .2, ..."""
        if index < 0:
            raise ValueError
        if index == 0:
            return 0
        if index == 1:
            return 1. / 1.2
        return 1. / (-1 + 2 * index)



class SainteLague14ApportionmentMethod(ApportionmentMethod):
    """Modified Sainte-Laguë Apportionment Method (first dv is 1.4)."""

    @classmethod
    def dv(cls, index: int) -> float:
        """(0) -> 0., (1) -> .7143, (2) -> .3333, (3) -> .2, ..."""
        if index < 0:
            raise ValueError
        if index == 0:
            return 0
        if index == 1:
            return 1. / 1.4
        return 1. / (-1 + 2 * index)


@dataclass
class ElectionResult:
    """Election result."""

    committees: list[set[Candidate]]
    scores: list[float]


@dataclass
class Election:
    """A way to run proportional approval voting election as simple as possible."""

    # Config
    committee_size: int
    apportionment_method: type[ApportionmentMethod]
    choices: set[Candidate] | None = None  # If None, isn't checked, got from ballots

    # State
    def __post_init__(self) -> None:
        """Set up state."""
        self.ballots = dict[int, Ballot]()
        self.ballot_to_indexes: dict[tuple[Candidate], list[int]] = defaultdict(list)
        self.counter = 0

    def cast_ballot(self, approves: Iterable[Candidate]) -> int:
        """Cast a ballot. This function does NOT check if the ballot is valid."""
        approves_set = set(approves)
        ballot_index = self.counter
        if ballot_index in self.ballots:
            msg = "Invariant breach"
            raise RuntimeError(msg)
        self.ballots[ballot_index] = approves_set
        self.ballot_to_indexes[tuple(sorted(approves_set))].append(ballot_index)
        self.counter += 1
        return ballot_index

    def remove_ballot(self, ballot: Ballot | int) -> None:
        """Remove ballot. If it doesn't exist, raise KeyError."""
        if isinstance(ballot, Ballot):
            ballot_index = self.ballot_to_indexes[tuple(sorted(ballot))][-1]
            ballot_value = ballot
        else:
            ballot_index = ballot
            ballot_value = self.ballots[ballot]
        del self.ballots[ballot_index]
        del self.ballot_to_indexes[ballot_value]

    def get_result(self) -> pd.DataFrame:
        """Get election result.

        It is NP-complete, so will hang with large enough committee size

        This function currently does not sort ballots into spoilt ones. It just
        removes incorrect candidates if self.choices is set.
        """
        actual_choices = set[Candidate]()
        for ballot in self.ballots.values():
            actual_choices |= ballot
        choices = actual_choices
        if self.choices is not None:
            choices &= self.choices
        best_committee_candidates: dict[float, tuple[set[Candidate]]] = {}
        for committee_candidate in combinations(choices, self.committee_size):
            committee_candidate_set = set(committee_candidate)
            committee_score = 0.
            for ballot in self.ballots.values():
                committee_score += self.apportionment_method.v(
                    len(ballot & committee_candidate_set)
                )
            # TODO(axxeny): #2 Support configurable number of best cases
            best_committee_candidates.setdefault(committee_score, []).append(
                tuple(sorted(committee_candidate)),
            )
        scores = sorted(best_committee_candidates.keys(), reverse=True)

        return pd.DataFrame({
            "committees": chain.from_iterable(
                best_committee_candidates[score] for score in scores
            ),
            "scores": chain.from_iterable(
                [score] * len(best_committee_candidates[score]) for score in scores
            ),
        }).sort_values(
            by=["scores", "committees"],
            ascending=[False, True],
            ignore_index=True,
        )
