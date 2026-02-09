## Installation

1. Install Python 3.12+ plus [uv](https://github.com/astral-sh/uv) or your preferred virtualenv manager.
2. Create/activate a virtual environment.
3. Install dependencies via `uv pip install -r pyproject.toml` (or `pip install -r requirements.txt` if you generate
   one).
4. Configure environment variables (`.env`) for the extractor/scorer: `EXTRACTION_MODEL_PROVIDER`, `EXTRACTION_MODEL`,
   and (if applicable) `OPENAI_API_KEY`.
5. Apply migrations with `python manage.py migrate`.

## Startup

```bash
cd cv_match
python manage.py runserver 0.0.0.0:9090
```

Swagger UI: `http://localhost:9090/api/docs/`  
OpenAPI schema: `http://localhost:9090/api/schema/`

To serve the static admin helpers:

```bash
python -m http.server 8000 --directory frontend
```

Then open `http://localhost:8000/manage_cvs.html` or `manage_job_offers.html`. They load `frontend/config.js` to
discover the API base (defaults to `http://localhost:9090/api`).

## Implementation approach

## Technical choices

- **Django + DRF** for viewsets, pagination, and routers.
- **drf-spectacular** for OpenAPI/Swagger generation.
- **pdfplumber**: To extract raw text from PDF.
- **mammoth**: To extract raw text from Docx.
- **LangChain + LLM providers** (OpenAI/Anthropic/Ollama) drive CV extraction and scoring.
- **Bootstrap + native JS**: lightweight admin pages in `frontend/` calling REST endpoints via `fetch`.
- **Logging**: simple `logging` config writing info logs to `logs/default.log` and errors to `logs/error.log`.
- **Codex**: As AI assistant to accomplish boring tasks

## Limitations

- Scoring/extraction strongly depend on external LLM APIs—without strong error handling or fallback in case of failure
  like internet access or something like that.
    - We can handle it by making more check and adding a fallback mechanism in case of internet or API failure.
- Currently unable to handle scanned PDF, it will be difficult to extract information for that.
    - We can handle that using an OCR implementation to be modest or a Vision-LLM for better handling.
- Static frontend is unauthenticated and minimal (no filtering, no pagination controls, no advanced UX).
- No automated tests are provided.
- Deterministic calculation of skills consider that all skills have the same importance
    - Can introduce a kind of weighted skills in the job offer creation
- Deterministic calculation of skills score is based on keyword matching which fragile. We can miss React.js because we
  were finding React.
    - Can use the tool thefuzz for similarity check instead of direct keywords mapping, and to go further we can use a
      richer embedding algorithm for similarity computation.
- The weights of each member of the final score are fixed in the code
    - We can add a kind of Singleton settings model to handle configuration like this one
- We don't care about the LLM context size when we do request to LLM
    - We can enable a chunking strategy or better model selection to prevent overflow

## Possible Improvements

- Improve scoring prompt to be more robust and to limit hallucination
- Add a feature to compute score of many CVs for the same offer
- Add a feature to extract useful information from a job offer
- Better UI
- Upgrade the platform to become a job research platform by storing both CV and Offer and implementing more complete
  RAG.

## Frontend configuration

`frontend/config.js` exports the API base URL:

```js
window.CV_MATCH_CONFIG = {
  apiBaseUrl: 'http://localhost:9090/api'
};
```

Update this file if you deploy the API elsewhere. Include it before the rest of the scripts (already done in the HTML
files).
