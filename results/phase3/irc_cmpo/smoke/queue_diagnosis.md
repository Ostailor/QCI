# QCi integer smoke queue diagnosis

- Job ID: `6a5ba9ef08442f441bbb20c2`
- Submitted/queued: `2026-07-18T16:29:35.868Z`
- Last checked in this diagnosis: `2026-07-18T17:14:08Z`
- API status: `QUEUED`
- Running timestamp: unavailable
- Completion timestamp: unavailable
- Job metrics: no execution metrics returned
- Problem config: `qudit_hamiltonian_optimization`
- Device config: `dirac-3_qudit`
- Declared levels: `[2, 2, 2, 2, 2, 2]`
- Samples requested: `30`
- Relaxation schedule: `2`
- `sum_constraint`: absent
- Allocation: paid, unmetered, 259200 seconds
- Uploaded polynomial: one part, 1794 bytes; the server-returned `file_config`
  exactly matches the preserved local request
- Subsequent smoke jobs submitted: `0`
- Duplicate/resubmitted jobs: `0`
- Projection used: `false`

The API accepted and preserved the documented integer job configuration and
polynomial. It returned neither a validation error nor a `running_at` timestamp.
QCi documents `QUEUED` as waiting for Dirac-3 to become available. The evidence
therefore isolates this delay to the service scheduler/device-availability path,
not the integer encoding, uploaded polynomial, credentials, or allocation.

The existing job must not be duplicated. Tests B and C remain blocked until the
native response for this job passes all strict smoke gates.
