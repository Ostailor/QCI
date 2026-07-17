# V1 Root Cause

The V1 builder copied each patch Hamiltonian and added a `budget_constraint` metadata object. It did not add variables or polynomial terms for the budget. Reconstruction later filtered portfolios by cost, which is valid as a post-hoc analysis but is not a budget-constrained hardware experiment. Encoding the full-system budget independently in twelve patch Hamiltonians would also be invalid because each patch could spend the entire system budget. V2 therefore uses one deduplicated global upgrade master per budget.
