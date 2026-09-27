# Healthcare Integration Learning Track

A daily, 48-session program on how US healthcare works end to end (payers, providers, members, CMS, PBMs, compliance) and how it is wired together (X12, HL7 v2, FHIR, NCPDP, interface engines, identity matching). Every sixth session is a hands-on lab built inside CMIP.

Each lesson follows the same arc: **problem and analogy -> objective -> who decides it -> business case -> approach (standards) -> integration view -> Medicare vs Medicaid vs Commercial -> conclusion**.

All data here is synthetic. No real PHI and no employer-proprietary material.

## Layout

| Path | What's in it |
| --- | --- |
| `notes/session-NN-<slug>.md` | Notes for each session, with the 30-second interview answer |
| `labs/lab-NN-<slug>/` | Code, configs and sample data for each lab, with a README (problem, approach, result, STAR story) |
| `../docker-compose.healthcare.yml` | HAPI FHIR server and Open Integration Engine (Mirth fork) for the labs |

Each session is committed and tagged `session-NN`, so `git log --oneline -- learning` and `git tag -l 'session-*'` show the learning history.

## Progress

| # | Session | Date | Tag |
| --- | --- | --- | --- |
