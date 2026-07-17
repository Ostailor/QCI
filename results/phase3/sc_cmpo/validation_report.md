# SC-CMPO Validation

Overall: **PASS**

| Check | Result | Detail |
|---|---:|---|
| payload_manifest_nonempty | PASS | payload_count=43 |
| all_payload_files_exist | PASS | all present |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:variable_count | PASS | 103 <= 132 |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:degree | PASS | degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:finite_coefficients | PASS | term_count=637 |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:scenario_count | PASS | scenario_count=8 |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:shared_first_stage | PASS | count=15 |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=157676800.0 |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case14_ieee__pglib_case14_ieee__patch_01__3-4.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case14_ieee.m |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:variable_count | PASS | 103 <= 132 |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:degree | PASS | degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:finite_coefficients | PASS | term_count=637 |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:scenario_count | PASS | scenario_count=8 |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:shared_first_stage | PASS | count=15 |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=85833920.0 |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case14_ieee__pglib_case14_ieee__patch_02__4-9.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case14_ieee.m |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:variable_count | PASS | 103 <= 132 |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:degree | PASS | degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:finite_coefficients | PASS | term_count=637 |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:scenario_count | PASS | scenario_count=8 |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:shared_first_stage | PASS | count=15 |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=49301760.00000001 |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case14_ieee__pglib_case14_ieee__patch_03__14-9.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case14_ieee.m |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:variable_count | PASS | 103 <= 132 |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:degree | PASS | degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:finite_coefficients | PASS | term_count=637 |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:scenario_count | PASS | scenario_count=8 |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:shared_first_stage | PASS | count=15 |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=31535360.000000004 |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case14_ieee__pglib_case14_ieee__patch_04__13-14.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case14_ieee.m |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:variable_count | PASS | 103 <= 132 |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:degree | PASS | degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:finite_coefficients | PASS | term_count=637 |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:scenario_count | PASS | scenario_count=8 |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:shared_first_stage | PASS | count=15 |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=27426880.000000004 |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case14_ieee__pglib_case14_ieee__patch_05__13-6.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case14_ieee.m |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:variable_count | PASS | 103 <= 132 |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:degree | PASS | degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:finite_coefficients | PASS | term_count=637 |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:scenario_count | PASS | scenario_count=8 |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:shared_first_stage | PASS | count=15 |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=42750400.0 |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case14_ieee__pglib_case14_ieee__patch_06__10-9.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case14_ieee.m |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:variable_count | PASS | 103 <= 132 |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:degree | PASS | degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:finite_coefficients | PASS | term_count=637 |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:scenario_count | PASS | scenario_count=8 |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:shared_first_stage | PASS | count=15 |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=61516160.00000001 |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case14_ieee__pglib_case14_ieee__patch_07__4-5.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case14_ieee.m |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:variable_count | PASS | 103 <= 132 |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:degree | PASS | degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:finite_coefficients | PASS | term_count=637 |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:scenario_count | PASS | scenario_count=8 |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:shared_first_stage | PASS | count=15 |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=21763840.0 |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case14_ieee__pglib_case14_ieee__patch_08__12-13.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case14_ieee.m |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:variable_count | PASS | 103 <= 132 |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:degree | PASS | degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:finite_coefficients | PASS | term_count=637 |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:scenario_count | PASS | scenario_count=8 |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:shared_first_stage | PASS | count=15 |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 14030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=16322880.000000002 |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case14_ieee__pglib_case14_ieee__patch_09__11-6.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case14_ieee.m |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:variable_count | PASS | 103 <= 132 |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:degree | PASS | degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:finite_coefficients | PASS | term_count=637 |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:scenario_count | PASS | scenario_count=8 |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:shared_first_stage | PASS | count=15 |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=129916800.00000001 |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case30_ieee__pglib_case30_ieee__patch_01__5-7.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case30_ieee.m |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:variable_count | PASS | 103 <= 132 |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:degree | PASS | degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:finite_coefficients | PASS | term_count=637 |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:scenario_count | PASS | scenario_count=8 |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:shared_first_stage | PASS | count=15 |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=33312000.000000004 |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case30_ieee__pglib_case30_ieee__patch_02__6-8.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case30_ieee.m |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:variable_count | PASS | 103 <= 132 |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:degree | PASS | degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:finite_coefficients | PASS | term_count=637 |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:scenario_count | PASS | scenario_count=8 |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:shared_first_stage | PASS | count=15 |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=25872320.000000004 |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case30_ieee__pglib_case30_ieee__patch_03__10-21.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case30_ieee.m |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:variable_count | PASS | 103 <= 132 |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:degree | PASS | degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:finite_coefficients | PASS | term_count=637 |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:scenario_count | PASS | scenario_count=8 |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:shared_first_stage | PASS | count=15 |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=21541760.0 |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case30_ieee__pglib_case30_ieee__patch_04__12-15.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case30_ieee.m |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:variable_count | PASS | 103 <= 132 |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:degree | PASS | degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:finite_coefficients | PASS | term_count=637 |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:scenario_count | PASS | scenario_count=8 |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:shared_first_stage | PASS | count=15 |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=14435200.000000002 |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case30_ieee__pglib_case30_ieee__patch_05__29-30.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case30_ieee.m |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:variable_count | PASS | 103 <= 132 |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:degree | PASS | degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:finite_coefficients | PASS | term_count=637 |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:scenario_count | PASS | scenario_count=8 |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:shared_first_stage | PASS | count=15 |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=14102080.000000002 |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case30_ieee__pglib_case30_ieee__patch_06__18-19.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case30_ieee.m |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:variable_count | PASS | 103 <= 132 |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:degree | PASS | degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:finite_coefficients | PASS | term_count=637 |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:scenario_count | PASS | scenario_count=8 |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:shared_first_stage | PASS | count=15 |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=16433920.000000002 |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case30_ieee__pglib_case30_ieee__patch_07__10-17.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case30_ieee.m |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:variable_count | PASS | 103 <= 132 |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:degree | PASS | degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:finite_coefficients | PASS | term_count=637 |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:scenario_count | PASS | scenario_count=8 |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:shared_first_stage | PASS | count=15 |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=13213760.000000002 |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case30_ieee__pglib_case30_ieee__patch_08__23-24.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case30_ieee.m |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:variable_count | PASS | 103 <= 132 |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:degree | PASS | degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:finite_coefficients | PASS | term_count=637 |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:scenario_count | PASS | scenario_count=8 |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:shared_first_stage | PASS | count=15 |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=20875520.0 |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case30_ieee__pglib_case30_ieee__patch_09__12-4.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case30_ieee.m |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:variable_count | PASS | 103 <= 132 |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:degree | PASS | degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:finite_coefficients | PASS | term_count=637 |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:scenario_count | PASS | scenario_count=8 |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:shared_first_stage | PASS | count=15 |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=19320960.0 |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case30_ieee__pglib_case30_ieee__patch_10__12-14.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case30_ieee.m |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:variable_count | PASS | 103 <= 132 |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:degree | PASS | degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:finite_coefficients | PASS | term_count=637 |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:scenario_count | PASS | scenario_count=8 |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:shared_first_stage | PASS | count=15 |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=16322880.000000002 |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case30_ieee__pglib_case30_ieee__patch_11__12-16.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case30_ieee.m |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:variable_count | PASS | 103 <= 132 |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:degree | PASS | degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:finite_coefficients | PASS | term_count=637 |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:scenario_count | PASS | scenario_count=8 |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:shared_first_stage | PASS | count=15 |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=3886400.0000000005 |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case30_ieee__pglib_case30_ieee__patch_12__25-26.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case30_ieee.m |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:variable_count | PASS | 103 <= 132 |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:degree | PASS | degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:finite_coefficients | PASS | term_count=637 |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:scenario_count | PASS | scenario_count=8 |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:shared_first_stage | PASS | count=15 |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=11104000.0 |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case30_ieee__pglib_case30_ieee__patch_13__3-4.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case30_ieee.m |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:schema | PASS | cmpo.sc_cmpo.v1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:variable_count | PASS | 103 <= 132 |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:variable_count_contract | PASS | actual=103 expected=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:unique_variable_names | PASS | unique=103 total=103 |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:degree | PASS | degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:finite_coefficients | PASS | term_count=637 |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:normalized_coefficients | PASS | max_abs=1 |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:scenario_count | PASS | scenario_count=8 |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:shared_first_stage | PASS | count=15 |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 30030, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:no_undocumented_synthetic_values | PASS | [] |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=12991680.000000002 |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| pglib_case30_ieee__pglib_case30_ieee__patch_14__19-20.json:source_provenance | PASS | https://raw.githubusercontent.com/power-grid-lib/pglib-opf/v23.07/pglib_opf_case30_ieee.m |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:schema | PASS | cmpo.sc_cmpo.v1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:variable_count | PASS | 103 <= 132 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:variable_count_contract | PASS | actual=103 expected=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:unique_variable_names | PASS | unique=103 total=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:degree | PASS | degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:finite_coefficients | PASS | term_count=637 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:normalized_coefficients | PASS | max_abs=1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:scenario_count | PASS | scenario_count=8 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:shared_first_stage | PASS | count=15 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:no_undocumented_synthetic_values | PASS | [] |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=133417891.20000002 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_01__320-321.json:source_provenance | PASS | https://data.openei.org/files/6153/Challenge_1_Original_Dataset_2_Scenarios.zip |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:schema | PASS | cmpo.sc_cmpo.v1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:variable_count | PASS | 103 <= 132 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:variable_count_contract | PASS | actual=103 expected=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:unique_variable_names | PASS | unique=103 total=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:degree | PASS | degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:finite_coefficients | PASS | term_count=637 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:normalized_coefficients | PASS | max_abs=1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:scenario_count | PASS | scenario_count=8 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:shared_first_stage | PASS | count=15 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:no_undocumented_synthetic_values | PASS | [] |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=131888870.4 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_02__21-22.json:source_provenance | PASS | https://data.openei.org/files/6153/Challenge_1_Original_Dataset_2_Scenarios.zip |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:schema | PASS | cmpo.sc_cmpo.v1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:variable_count | PASS | 103 <= 132 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:variable_count_contract | PASS | actual=103 expected=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:unique_variable_names | PASS | unique=103 total=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:degree | PASS | degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:finite_coefficients | PASS | term_count=637 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:normalized_coefficients | PASS | max_abs=1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:scenario_count | PASS | scenario_count=8 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:shared_first_stage | PASS | count=15 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:no_undocumented_synthetic_values | PASS | [] |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=117687964.80000001 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_03__3-4.json:source_provenance | PASS | https://data.openei.org/files/6153/Challenge_1_Original_Dataset_2_Scenarios.zip |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:schema | PASS | cmpo.sc_cmpo.v1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:variable_count | PASS | 103 <= 132 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:variable_count_contract | PASS | actual=103 expected=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:unique_variable_names | PASS | unique=103 total=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:degree | PASS | degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:finite_coefficients | PASS | term_count=637 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:normalized_coefficients | PASS | max_abs=1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:scenario_count | PASS | scenario_count=8 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:shared_first_stage | PASS | count=15 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:no_undocumented_synthetic_values | PASS | [] |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=111118838.4 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_04__228-474.json:source_provenance | PASS | https://data.openei.org/files/6153/Challenge_1_Original_Dataset_2_Scenarios.zip |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:schema | PASS | cmpo.sc_cmpo.v1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:variable_count | PASS | 103 <= 132 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:variable_count_contract | PASS | actual=103 expected=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:unique_variable_names | PASS | unique=103 total=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:degree | PASS | degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:finite_coefficients | PASS | term_count=637 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:normalized_coefficients | PASS | max_abs=1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:scenario_count | PASS | scenario_count=8 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:shared_first_stage | PASS | count=15 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:no_undocumented_synthetic_values | PASS | [] |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=133223571.20000002 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_05__485-499.json:source_provenance | PASS | https://data.openei.org/files/6153/Challenge_1_Original_Dataset_2_Scenarios.zip |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:schema | PASS | cmpo.sc_cmpo.v1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:variable_count | PASS | 103 <= 132 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:variable_count_contract | PASS | actual=103 expected=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:unique_variable_names | PASS | unique=103 total=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:degree | PASS | degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:finite_coefficients | PASS | term_count=637 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:normalized_coefficients | PASS | max_abs=1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:scenario_count | PASS | scenario_count=8 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:shared_first_stage | PASS | count=15 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:no_undocumented_synthetic_values | PASS | [] |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=107381232.00000001 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_06__326-327.json:source_provenance | PASS | https://data.openei.org/files/6153/Challenge_1_Original_Dataset_2_Scenarios.zip |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:schema | PASS | cmpo.sc_cmpo.v1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:variable_count | PASS | 103 <= 132 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:variable_count_contract | PASS | actual=103 expected=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:unique_variable_names | PASS | unique=103 total=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:degree | PASS | degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:finite_coefficients | PASS | term_count=637 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:normalized_coefficients | PASS | max_abs=1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:scenario_count | PASS | scenario_count=8 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:shared_first_stage | PASS | count=15 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:no_undocumented_synthetic_values | PASS | [] |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=106016550.4 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_07__263-491.json:source_provenance | PASS | https://data.openei.org/files/6153/Challenge_1_Original_Dataset_2_Scenarios.zip |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:schema | PASS | cmpo.sc_cmpo.v1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:variable_count | PASS | 103 <= 132 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:variable_count_contract | PASS | actual=103 expected=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:unique_variable_names | PASS | unique=103 total=103 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:degree | PASS | degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:finite_coefficients | PASS | term_count=637 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:normalized_coefficients | PASS | max_abs=1 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:scenario_count | PASS | scenario_count=8 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:shared_first_stage | PASS | count=15 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 1020, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:no_undocumented_synthetic_values | PASS | [] |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=97536425.60000001 |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| arpae_go_network_01o_020__arpae_go_network_01o_020__patch_08__141-142.json:source_provenance | PASS | https://data.openei.org/files/6153/Challenge_1_Original_Dataset_2_Scenarios.zip |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:schema | PASS | cmpo.sc_cmpo.v1 |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:variable_count | PASS | 103 <= 132 |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:variable_count_contract | PASS | actual=103 expected=103 |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:unique_variable_names | PASS | unique=103 total=103 |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:degree | PASS | degree=3 |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:finite_coefficients | PASS | term_count=637 |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:normalized_coefficients | PASS | max_abs=1 |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:scenario_count | PASS | scenario_count=8 |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:shared_first_stage | PASS | count=15 |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:no_undocumented_synthetic_values | PASS | [] |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=338672.0 |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| ieee123_opendss__ieee123_opendss__patch_01__76-77-86.json:source_provenance | PASS | https://github.com/dss-extensions/electricdss-tst/tree/3b208397160213cae4a9e2d0a7d1aa3528ce26e1/Version8/Distrib/IEEETestCases/123Bus |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:schema | PASS | cmpo.sc_cmpo.v1 |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:variable_count | PASS | 103 <= 132 |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:variable_count_contract | PASS | actual=103 expected=103 |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:unique_variable_names | PASS | unique=103 total=103 |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:degree | PASS | degree=3 |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:finite_coefficients | PASS | term_count=637 |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:normalized_coefficients | PASS | max_abs=1 |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:scenario_count | PASS | scenario_count=8 |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:shared_first_stage | PASS | count=15 |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:no_undocumented_synthetic_values | PASS | [] |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=505232.00000000006 |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| ieee123_opendss__ieee123_opendss__patch_02__47-48-49.json:source_provenance | PASS | https://github.com/dss-extensions/electricdss-tst/tree/3b208397160213cae4a9e2d0a7d1aa3528ce26e1/Version8/Distrib/IEEETestCases/123Bus |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:schema | PASS | cmpo.sc_cmpo.v1 |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:variable_count | PASS | 103 <= 132 |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:variable_count_contract | PASS | actual=103 expected=103 |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:unique_variable_names | PASS | unique=103 total=103 |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:degree | PASS | degree=3 |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:finite_coefficients | PASS | term_count=637 |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:normalized_coefficients | PASS | max_abs=1 |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:scenario_count | PASS | scenario_count=8 |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:shared_first_stage | PASS | count=15 |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:no_undocumented_synthetic_values | PASS | [] |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=322016.0 |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| ieee123_opendss__ieee123_opendss__patch_03__64-65-66.json:source_provenance | PASS | https://github.com/dss-extensions/electricdss-tst/tree/3b208397160213cae4a9e2d0a7d1aa3528ce26e1/Version8/Distrib/IEEETestCases/123Bus |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:schema | PASS | cmpo.sc_cmpo.v1 |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:variable_count | PASS | 103 <= 132 |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:variable_count_contract | PASS | actual=103 expected=103 |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:unique_variable_names | PASS | unique=103 total=103 |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:degree | PASS | degree=3 |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:finite_coefficients | PASS | term_count=637 |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:normalized_coefficients | PASS | max_abs=1 |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:scenario_count | PASS | scenario_count=8 |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:shared_first_stage | PASS | count=15 |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:no_undocumented_synthetic_values | PASS | [] |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=133248.0 |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| ieee123_opendss__ieee123_opendss__patch_04__100-98-99.json:source_provenance | PASS | https://github.com/dss-extensions/electricdss-tst/tree/3b208397160213cae4a9e2d0a7d1aa3528ce26e1/Version8/Distrib/IEEETestCases/123Bus |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:schema | PASS | cmpo.sc_cmpo.v1 |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:variable_count | PASS | 103 <= 132 |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:variable_count_contract | PASS | actual=103 expected=103 |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:unique_variable_names | PASS | unique=103 total=103 |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:degree | PASS | degree=3 |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:finite_coefficients | PASS | term_count=637 |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:normalized_coefficients | PASS | max_abs=1 |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:scenario_count | PASS | scenario_count=8 |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:shared_first_stage | PASS | count=15 |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:no_undocumented_synthetic_values | PASS | [] |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=133248.0 |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| ieee123_opendss__ieee123_opendss__patch_05__73-74-75.json:source_provenance | PASS | https://github.com/dss-extensions/electricdss-tst/tree/3b208397160213cae4a9e2d0a7d1aa3528ce26e1/Version8/Distrib/IEEETestCases/123Bus |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:schema | PASS | cmpo.sc_cmpo.v1 |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:variable_count | PASS | 103 <= 132 |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:variable_count_contract | PASS | actual=103 expected=103 |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:unique_variable_names | PASS | unique=103 total=103 |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:degree | PASS | degree=3 |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:finite_coefficients | PASS | term_count=637 |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:normalized_coefficients | PASS | max_abs=1 |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:scenario_count | PASS | scenario_count=8 |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:shared_first_stage | PASS | count=15 |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:no_undocumented_synthetic_values | PASS | [] |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=66624.0 |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| ieee123_opendss__ieee123_opendss__patch_06__3-5-6.json:source_provenance | PASS | https://github.com/dss-extensions/electricdss-tst/tree/3b208397160213cae4a9e2d0a7d1aa3528ce26e1/Version8/Distrib/IEEETestCases/123Bus |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:schema | PASS | cmpo.sc_cmpo.v1 |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:variable_count | PASS | 103 <= 132 |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:variable_count_contract | PASS | actual=103 expected=103 |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:unique_variable_names | PASS | unique=103 total=103 |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:degree | PASS | degree=3 |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:finite_coefficients | PASS | term_count=637 |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:normalized_coefficients | PASS | max_abs=1 |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:scenario_count | PASS | scenario_count=8 |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:shared_first_stage | PASS | count=15 |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:no_undocumented_synthetic_values | PASS | [] |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=283152.0 |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| ieee123_opendss__ieee123_opendss__patch_07__63-64-65.json:source_provenance | PASS | https://github.com/dss-extensions/electricdss-tst/tree/3b208397160213cae4a9e2d0a7d1aa3528ce26e1/Version8/Distrib/IEEETestCases/123Bus |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:schema | PASS | cmpo.sc_cmpo.v1 |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:variable_count | PASS | 103 <= 132 |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:variable_count_contract | PASS | actual=103 expected=103 |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:unique_variable_names | PASS | unique=103 total=103 |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:degree | PASS | degree=3 |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:finite_coefficients | PASS | term_count=637 |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:normalized_coefficients | PASS | max_abs=1 |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:scenario_count | PASS | scenario_count=8 |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:shared_first_stage | PASS | count=15 |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:no_undocumented_synthetic_values | PASS | [] |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=111040.00000000001 |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| ieee123_opendss__ieee123_opendss__patch_08__69-70-71.json:source_provenance | PASS | https://github.com/dss-extensions/electricdss-tst/tree/3b208397160213cae4a9e2d0a7d1aa3528ce26e1/Version8/Distrib/IEEETestCases/123Bus |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:schema | PASS | cmpo.sc_cmpo.v1 |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:variable_count | PASS | 103 <= 132 |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:variable_count_contract | PASS | actual=103 expected=103 |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:unique_variable_names | PASS | unique=103 total=103 |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:degree | PASS | degree=3 |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:finite_coefficients | PASS | term_count=637 |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:normalized_coefficients | PASS | max_abs=1 |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:scenario_count | PASS | scenario_count=8 |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:shared_first_stage | PASS | count=15 |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:no_undocumented_synthetic_values | PASS | [] |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=88832.0 |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| ieee123_opendss__ieee123_opendss__patch_09__112-113-114.json:source_provenance | PASS | https://github.com/dss-extensions/electricdss-tst/tree/3b208397160213cae4a9e2d0a7d1aa3528ce26e1/Version8/Distrib/IEEETestCases/123Bus |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:schema | PASS | cmpo.sc_cmpo.v1 |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:variable_count | PASS | 103 <= 132 |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:variable_count_contract | PASS | actual=103 expected=103 |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:unique_variable_names | PASS | unique=103 total=103 |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:degree | PASS | degree=3 |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:finite_coefficients | PASS | term_count=637 |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:normalized_coefficients | PASS | max_abs=1 |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:scenario_count | PASS | scenario_count=8 |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:shared_first_stage | PASS | count=15 |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:no_undocumented_synthetic_values | PASS | [] |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=133248.0 |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| ieee123_opendss__ieee123_opendss__patch_10__28-29-30.json:source_provenance | PASS | https://github.com/dss-extensions/electricdss-tst/tree/3b208397160213cae4a9e2d0a7d1aa3528ce26e1/Version8/Distrib/IEEETestCases/123Bus |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:schema | PASS | cmpo.sc_cmpo.v1 |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:variable_count | PASS | 103 <= 132 |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:variable_count_contract | PASS | actual=103 expected=103 |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:unique_variable_names | PASS | unique=103 total=103 |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:degree | PASS | degree=3 |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:finite_coefficients | PASS | term_count=637 |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:normalized_coefficients | PASS | max_abs=1 |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:scenario_count | PASS | scenario_count=8 |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:shared_first_stage | PASS | count=15 |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:no_undocumented_synthetic_values | PASS | [] |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=88832.0 |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| ieee123_opendss__ieee123_opendss__patch_11__15-16-34.json:source_provenance | PASS | https://github.com/dss-extensions/electricdss-tst/tree/3b208397160213cae4a9e2d0a7d1aa3528ce26e1/Version8/Distrib/IEEETestCases/123Bus |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:schema | PASS | cmpo.sc_cmpo.v1 |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:variable_count | PASS | 103 <= 132 |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:variable_count_contract | PASS | actual=103 expected=103 |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:unique_variable_names | PASS | unique=103 total=103 |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:bounded_variables | PASS | all variables must have exact [0,1] bounds |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:degree | PASS | degree=3 |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:finite_coefficients | PASS | term_count=637 |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:normalized_coefficients | PASS | max_abs=1 |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:qci_export_contract | PASS | num_variables=103; max_degree=3 |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:scenario_count | PASS | scenario_count=8 |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:unique_scenarios | PASS | normal,renewable_shortfall,demand_surge,pcc_loss,local_generator_loss,forced_islanding,restoration,combined_high_stress |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:shared_first_stage | PASS | count=15 |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:challenge_stages | PASS | upgrade_planning,pre_event_preparedness,emergency_response,restoration |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:public_inputs_only | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:no_random_grid_values | PASS | {'public_inputs_only': True, 'random_topology_or_asset_values': False, 'undocumented_synthetic_values': [], 'deterministic_seed': 123, 'seed_use': 'SHA-256 tie-breaking only; no random-number generator is invoked'} |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:no_undocumented_synthetic_values | PASS | [] |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:nonzero_upgrade_structural | PASS | robust_island=True; min_cost=111040.00000000001 |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:qci_not_mislabeled | PASS | SC-CMPO build-only public-data artifact; not submitted to QCi. |
| ieee123_opendss__ieee123_opendss__patch_12__86-87-88.json:source_provenance | PASS | https://github.com/dss-extensions/electricdss-tst/tree/3b208397160213cae4a9e2d0a7d1aa3528ce26e1/Version8/Distrib/IEEETestCases/123Bus |
| at_least_three_public_families | PASS | arpae_go_challenge1,ieee123_distribution,pglib_case14_ieee,pglib_case30_ieee |
| manifest_qci_not_executed | PASS | all rows must remain build-only |
| positive_upgrade_case | PASS | at least one robust island requires a nonzero upgrade |
| provenance_complete | PASS | rows=11 |
| local_provenance_checksums | PASS | every local provenance file matches its recorded checksum |
| source_checksums_recorded | PASS | every upstream source checksum is a SHA-256 digest |
| nonzero_stage1_decision_evidence | PASS | robust_lp_present=True; robust_lp_nonzero=True |
