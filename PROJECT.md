# PROJECT

The locked settings and decisions of the current campaign. Written by `calculation_protocol`, locked at the approve-settings checkpoint; every tool reads it and none changes a locked value. The fields are `fragplace.schemas.records.Settings`; the human answers of the Formulate interview sit under *Interview*. This is the template; `fragplace init <campaign>` copies it into `runs/<campaign>/`.

settings hash: `not locked`

```yaml
{
  "metal": "Pt",
  "facet": "111",
  "adsorbate": "OH",
  "product": [
    "O",
    "H"
  ],
  "functional": "RPBE",
  "dispersion": null,
  "spin_polarised": false,
  "initial_moments": {},
  "hubbard_u": {},
  "pseudopotential_family": "PAW",
  "pseudopotential_version": null,
  "cutoff_eV": 350.0,
  "kmesh": null,
  "smearing": "Methfessel-Paxton",
  "sigma_eV": 0.1,
  "layers": 4,
  "fixed_layers": 2,
  "vacuum_A": 15.0,
  "dipole_correction": true,
  "cell_repeat": null,
  "min_image_distance_A": 10.0,
  "force_threshold_eV_per_A": 0.03,
  "scf_threshold_eV": 1e-05,
  "convergence_target_meV": null,
  "gas_references": [],
  "protocol": null,
  "protocol_reason": null,
  "mlip": null,
  "mlip_committee": [],
  "decisions": {
    "structure_retrieval.image_measure": null,
    "calculation_protocol.convergence_target_meV": null,
    "calculation_protocol.gas_references": null,
    "mlip_selection.candidates": null,
    "mlip_selection.label_count": null,
    "adsorbate_placement.displacement_amplitude_A": null,
    "adsorbate_placement.fragment_A_fixed_at_old_site": null,
    "pair_enumeration.d_definition": null,
    "pair_enumeration.upper_bound_A": null,
    "pull_force_screen.threshold_eV_per_A": null,
    "anomaly_filter.AB_bond_reformed_A": null,
    "anomaly_filter.migrated": null,
    "anomaly_filter.dissociated": null,
    "anomaly_filter.reconstructed": null,
    "anomaly_filter.imaginary_noise_cm": null,
    "anomaly_filter.expected_range_width_eV": null,
    "anomaly_filter.magnetism_collapsed": null,
    "anomaly_filter.intercalated": null,
    "anomaly_filter.frequencies_source": null,
    "soap_clustering.per_cluster": null,
    "uncertainty_estimation.escalation_threshold_eV": null,
    "uncertainty_estimation.label_count": null,
    "ranking.shortlist_size": null
  },
  "locked": false,
  "approved_by": null,
  "approved_at": null
}
```

## Interview

Five questions the human answers before anything runs; each answer becomes a check, a prior or a skill line.

| Question | Answer |
|---|---|
| What do you check first when an adsorption energy looks wrong? | |
| Which defaults of the code do you distrust for this system? | |
| What must hold before you trust a machine-learned potential here? | |
| Which published values should the result be compared with, with functional and site? | |
| What has silently gone wrong before on a system like this? | |

## Decisions

| Decision | Status |
|---|---|
| D1 first system and product: *OH → *O + *H on Pt(111) | open: team decision |
| D2 DFT code, compute, GPU; any DFT at all | open: team decision |
| D3 OC20NEB subset as ground truth; pass criterion | open: team decision |
| D4 headline claim | open: team decision |
| D5 final-state rules: distance metric, A fixed or enumerated, nearest or lowest within one hop | open: team decision |

Every threshold marked open in the registry sits under `decisions` above as null; `fragplace decisions` lists them with what each means. `calculation_protocol` refuses the lock while any is null.
