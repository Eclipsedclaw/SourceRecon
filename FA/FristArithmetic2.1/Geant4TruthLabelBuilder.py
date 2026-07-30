import numpy as np


class Geant4TruthLabelBuilder:
    """Attach training-only labels to enumerated candidate events.

    Candidate construction already enforces different detector layers and,
    with back-scattering disabled, increasing layer order.  Training therefore
    needs only two targets:

        y_same_gamma:
            all candidate hits belong to the same Geant4 event ID;

        y_full_absorption:
            for a same-gamma candidate, the sum of its selected deposited
            energies agrees with that dataset's primary-energy truth.

    Primary energy is used only to create the second label.  It is never added
    to candidate features.
    """

    def __init__(
        self,
        event_list,
        event_truth_df,
        energy_tolerance_mev=0.03,
    ):
        self.event_list = event_list
        self.event_truth_df = event_truth_df
        self.energy_tolerance_mev = energy_tolerance_mev
        self.truth_by_event = self._index_truth()

    def _index_truth(self):
        truth = {}
        for _, row in self.event_truth_df.iterrows():
            truth[row["true_event_id"]] = {
                "primary_energy": row.get("primary_energy", np.nan),
            }
        return truth

    def apply(self):
        for event in self.event_list.events:
            self._label_event(event)
        return self.event_list

    def _label_event(self, event):
        true_ids = list(getattr(event, "true_event_ids", []))
        valid_ids = [value for value in true_ids if value is not None]
        y_same_gamma = int(
            len(valid_ids) == len(true_ids)
            and len(valid_ids) > 0
            and len(set(valid_ids)) == 1
        )

        # Candidate generation already guarantees increasing, different-layer
        # order.  No time-based rejection is applied while back-scattering is
        # disabled.
        event.y_correct_order = 1
        event.order_label_source = "increasing_layer_assumption"

        primary_energy = np.nan
        y_full_absorption = None
        if y_same_gamma == 1:
            truth = self.truth_by_event.get(valid_ids[0])
            if truth is not None:
                primary_energy = float(truth["primary_energy"])
                if not np.isnan(primary_energy):
                    candidate_energy = float(getattr(event, "E_total", np.nan))
                    y_full_absorption = int(
                        not np.isnan(candidate_energy)
                        and abs(candidate_energy - primary_energy)
                        < self.energy_tolerance_mev
                    )

        event.y_same_gamma = y_same_gamma
        event.y_match_correct = y_same_gamma
        event.y_full_absorption = y_full_absorption

        # Compatibility aliases used by the existing trainer and reports.
        # Candidate completeness is no longer an independent hard condition.
        event.y_event_full = y_full_absorption
        event.y_candidate_complete = None
        event.y_complete_full = y_full_absorption
        event.y_match = y_same_gamma
        event.y_full = y_full_absorption
        event.y_usable = y_full_absorption

        # Training-only diagnostic.  The scorer never reads this attribute.
        event.label_primary_energy_mev = primary_energy
