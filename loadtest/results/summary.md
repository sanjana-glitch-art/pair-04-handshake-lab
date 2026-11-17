# JMeter results

## CRUD endpoints

| Endpoint | Users | Samples | Avg ms | p95 ms | Throughput req/s | Error % |
|---|---|---|---|---|---|---|
| Login | 100 | 500 | 1106.9 | 2001.6 | 41.16 | 0.0 |
| Login | 200 | 1000 | 2254.1 | 4037.1 | 70.59 | 0.0 |
| Login | 300 | 1500 | 2977.7 | 4984.1 | 57.26 | 0.0 |
| Login | 400 | 2000 | 4570.1 | 7437.1 | 61.89 | 0.0 |
| Login | 500 | 2500 | 5329.9 | 9175.0 | 43.95 | 0.0 |
| Job search | 100 | 2000 | 291.3 | 963.0 | 169.88 | 0.0 |
| Job search | 200 | 4000 | 432.5 | 914.0 | 230.8 | 0.0 |
| Job search | 300 | 6000 | 366.0 | 733.1 | 628.34 | 0.0 |
| Job search | 400 | 8000 | 487.3 | 1402.0 | 578.87 | 0.0 |
| Job search | 500 | 10000 | 864.4 | 1898.0 | 415.33 | 0.0 |
| Application submission | 100 | 100 | 51.0 | 161.0 | 69.88 | 0.0 |
| Application submission | 200 | 200 | 373.5 | 929.1 | 44.84 | 0.0 |
| Application submission | 300 | 300 | 45.1 | 141.0 | 87.21 | 0.0 |
| Application submission | 400 | 400 | 81.6 | 259.1 | 92.98 | 0.0 |
| Application submission | 500 | 500 | 272.2 | 815.0 | 54.23 | 0.0 |
| Event search | 100 | 2000 | 109.9 | 192.0 | 492.25 | 0.0 |
| Event search | 200 | 4000 | 79.4 | 194.0 | 829.02 | 0.0 |
| Event search | 300 | 6000 | 385.6 | 759.1 | 354.3 | 0.0 |
| Event search | 400 | 8000 | 626.1 | 1267.0 | 531.03 | 0.0 |
| Event search | 500 | 10000 | 901.1 | 1955.0 | 493.88 | 0.0 |

## Assistant

Error % counts every request that did not end with an answer (status `final`), taken from the traces; HTTP-level errors were 0% because the API returns 200 with status `model_error` or `timeout`.

| Users | Samples | p50 s | p95 s | p99 s | Avg s | Error % | Outcomes |
|---|---|---|---|---|---|---|---|
| 5 | 5 | 294.8 | 360.1 | 365.9 | 291.2 | 0.0 | final 5 |
| 10 | 10 | 367.1 | 496.5 | 508.6 | 375.0 | 90.0 | final 1, model_error 2, timeout 3, no trace 4 (laptop suspended; counted as errors) |
| 20 | 20 | 349.5 | 485.0 | 508.4 | 357.0 | 100.0 | model_error 16, timeout 4 |
| 50 | 50 | 300.3 | 479.9 | 513.2 | 345.9 | 100.0 | model_error 48, timeout 2 |
