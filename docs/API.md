# API

All application routes use `/api/v1`. Except for health/readiness and login/refresh, requests require `Authorization: Bearer <access-token>`.

| Route | Purpose |
| --- | --- |
| `POST /auth/login` | Authenticate and register/update an installation device. |
| `POST /auth/refresh`, `POST /auth/logout` | Rotate or revoke refresh tokens. |
| `GET /devices/me` | Return the authenticated user and device. |
| `POST /jobs` | Create a `single` or `group` job. |
| `POST /jobs/{id}/images` | Upload one JPEG or PNG image. |
| `POST /jobs/{id}/submit` | Queue the job. |
| `GET /jobs`, `GET /jobs/{id}`, `GET /jobs/{id}/result` | List, poll, and retrieve results. |
| `GET /jobs/{id}/artifacts/{artifact}` | Fetch an owned result image, crop, or mask. |
| `GET /jobs/labels`, `POST /jobs/{id}/confirm` | Retrieve valid types and persist reviewed labels. |

Jobs move from `created` to `queued`, `processing`, then `completed` or `failed`. Results include count, per-piece labels, review flags, timing data, and artifact names.
