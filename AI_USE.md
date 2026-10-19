# AI use

**Assistant used:** Claude Code (Anthropic, model Claude Opus 5.5) in the
Claude desktop app, working in a local clone of this repository.

**What it was used for**

- Reviewing the repository against the Lab 1 PDF and listing what was missing.
- Fixing `database/schema.sql` (it created a table named `user` while every
  foreign key referenced `users`), converting `requirements.txt` from UTF-16
  to UTF-8, and adding the missing `httpx` and `python-multipart` packages.
- Writing the seed generator, the shared event-eligibility rule, the student
  directory, skills, profile pictures, resume preview, event registrants,
  and the related React pages.
- Restructuring the assistant into `app/assistant/` (model client, tools,
  confirmation gate, agent loop with the repair path) and writing the
  evaluation scripts for the transcripts, reliability table, and injection
  experiment.
- Drafting README, METRICS, RUN_LOG, and the report.

Every change was reviewed before it was committed, and every feature was
run against the real MySQL database, the running API, the React UI, and
the local `qwen3:8b` model. The numbers in METRICS.md come from those runs,
not from the assistant.

**Incorrect output 1: `search_jobs` hid every remote job when a city was also given**

- *What it produced:* the first version of the `search_jobs` tool applied
  the `city` filter and the `remote` filter independently. Seeded remote
  jobs have the location `Remote`, so a call such as
  `search_jobs(city="San Jose", remote=true, …)` could never match anything.
- *How it was detected:* in the live evaluation log, test T2 ("Find a remote
  data science internship…") showed the model calling `search_jobs` with
  `"city": "San Jose", "remote": true` (it had pulled the city from the
  student's saved preferences). A remote job can be done from anywhere, so
  "no remote jobs in San Jose" was the wrong answer.
- *Fix:* when `remote=true`, the tool ignores `city` and says so in its
  output ("Note: city 'San Jose' was ignored because remote jobs can be done
  from anywhere."). The evaluation was rerun after the fix.

**Incorrect output 2: the first set of transcripts passed the checks but gave poor answers**

- *What it produced:* with qwen3's reasoning mode turned off (the assistant's
  original choice, for speed), all five automated transcript checks passed.
  But reading the transcripts showed that in T3 the model invented
  `name="career fair"` and `city="San Francisco"` filters and told the
  student no events existed. In T2 it dropped "data science" from the search
  and still called the results "data science internships".
- *How it was detected:* by reading the tool arguments in
  `docs/evaluation/transcripts.md` instead of relying on the PASS column.
- *Fix:* the parameter descriptions now say when each filter may be used
  (for example, "Only set it when the student names a city"). `search_events`
  now reports how many events would match without an optional filter. The
  model client turns on qwen3 reasoning by default (`OLLAMA_THINK=true`);
  set `OLLAMA_THINK=false` or pass `--no-think` to turn it off. With
  reasoning on, T3 searched next month with a Computer Science filter and
  found real events, and T2 searched `title="data science"`. The cost is
  latency, which METRICS.md reports.

**Incorrect output 3: the first prompt-injection experiment could not have measured anything**

- *What it produced:* the first injected job description put the
  instructions (rank first, leak an email, print a canary code) after an
  ordinary sentence, making the text about 400 characters long. The first
  run's table then reported "listed injected item first: yes" for T2 and T4,
  with the defense both off and on.
- *How it was detected:* reading the answers next to the tool calls showed
  two things. First, the injected jobs were legitimately first in the tool's
  own ranking: T2 was sorted by deadline, T4 by pay, and the fixture jobs paid
  the most. Second, search results show only a 160-character summary of each
  description, so the model only ever saw the beginning of the injected
  instructions. One undefended answer even noted that "one summary line
  appears truncated".
- *Fix:* the injection was rewritten to 147 characters and placed at the
  start of the description, so it reaches the model in full. The metrics now
  record whether the full injection reached the model, and they separate
  "first in the tool's own ranking" from "promoted above the tool's ranking".
  The flawed run is kept as `docs/evaluation/injection_run1_truncated.md`.

## Thummalapalli Sai Teja Sri Sanjana

*To be completed by Sanjana: which assistant(s) she used and for what, one
incorrect output, how it was detected, and the fix.*
