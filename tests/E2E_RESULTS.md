# Docker end-to-end verification

Verified on 2026-11-03 using Docker Desktop Linux containers and the browser
at `http://127.0.0.1:8080/`.

Flow: browser JavaScript → Nginx frontend → FastAPI backend → LangGraph
model/tool loop → OpenAI and MCP sales service → answer displayed in browser.
The Q2 and Q4 scenarios used live OpenAI requests, not scripted responses.

| Scenario | Expected result | Observed result | Outcome |
| --- | --- | --- | --- |
| Q2 sales comparison | Actual 200, target 300, variance -33.33% | Browser displayed all figures and stated sales were 33.33% below target | Pass |
| Loading state | Feedback and disabled submit button | “Analyzing…” button disabled; “Working” status displayed | Pass |
| Q4 missing data | Explain unavailable data without fabricated figures | Browser stated the period was not found and variance could not be calculated | Pass |
| Whitespace prompt in browser | Reject locally | “Enter a sales question first.” validation message | Pass |
| Quarter example after validation | Restore usable prompt | Q2 example replaced the prompt and dismissed the validation message | Pass |
| Invalid HTTP requests through frontend proxy | HTTP 422 | Missing, empty, whitespace-only, and over-4000-character prompts each returned 422 | Pass |
| Container health | Three healthy services | Frontend, backend, and MCP all healthy | Pass |

Evidence: `evidence/q4-missing-data.png` captures the rendered missing-data
answer. `evidence/q2-request.png` captures the Q2 request layout; the Q2
answer was verified through the browser accessibility state.

## Repeat manually

1. Configure your own key and accessible model in `.env`.
2. Run `docker compose up --build -d --wait` from the project root.
3. Open `http://127.0.0.1:8080/` and submit the default Q2 question.
4. Confirm actual 200, target 300, and variance -33.33%.
5. Change the period to 2026-Q4, submit, and confirm the answer explains
   missing data rather than giving invented figures.
6. Enter spaces only and submit; confirm local validation blocks the request.
7. Choose a quarter example and confirm it restores a valid prompt.
8. Run `docker compose ps` and confirm all three services are healthy.

Live scenarios incur API usage. This records the tested local Docker
deployment; it does not claim public hosting, load testing, or exhaustive
failure testing. Missing configuration and agent failure behavior are covered
separately by `check_backend.py` with test doubles.
