"""An example of axvoting.cardinal.approval.proportional.Election usage."""

from axvoting.cardinal.approval.proportional import (
    ApportionmentMethod,
    Election,
)

e = Election(
    committee_size=3,
    apportionment_method=ApportionmentMethod.from_name("sainte_lague"),
)
e.cast_ballot({"A", "B", "C"})
e.cast_ballot({"A", "B", "X"})
e.cast_ballot({"A", "B", "C"})
e.cast_ballot({"A", "B", "X"})
e.cast_ballot({"A", "B", "C"})
e.cast_ballot({"A", "B", "X"})
e.cast_ballot({"X", "Y", "Z"})
e.get_result()
