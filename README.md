# Six-Man Rankings

Canonical source: **https://github.com/rcullens/ranking-tool**

A standalone Python toolkit that publishes **objective Texas UIL six-man high school football power rankings**, with a live Thu–Fri–Sat score pull so the list and comparison graph update as finals land.

The model is built for a league where Friday nights are high-scoring, mercy-rule endings are common, entire two-way lineups graduate in one May, and a 10–0 district champion may never have left its own county. Bundled synthetic fixtures — real program names, a fictional slate — let you run the pipeline without credentials. Point `SIXMAN_FEED_URL` at a JSON score feed (or `POST /api/ingest`) for a real Friday night.
