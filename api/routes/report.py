# api/routes/report.py — full RAG report: retrieval + scoring + enrichment +
# LLM-generated citation-backed assessment and opposition draft.

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from api.deps import get_engine, get_llm_client, resolve_entry
from api.schemas import AnalyzeIn
from src.rag import retriever, report_generator
from src.report import renderer

router = APIRouter(prefix="/api/report", tags=["report"])


def _build(req: AnalyzeIn) -> dict:
    entry = resolve_entry(
        tk_id=req.tk_id,
        practice_name=req.practice_name,
        description=req.description,
        country=req.country,
        documentation_date=req.documentation_date,
    )
    context = retriever.build_context(entry, get_engine(), n_results=req.n_results)
    return report_generator.generate_report(entry, context, llm=get_llm_client())


@router.post("")
def make_report(req: AnalyzeIn, format: str = Query("json", pattern="^(json|markdown|pdf)$")) -> Response:
    try:
        report = _build(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if format == "markdown":
        return PlainTextResponse(renderer.to_markdown(report), media_type="text/markdown")
    if format == "pdf":
        return Response(renderer.to_pdf(report), media_type="application/pdf")
    # default json — include rendered markdown for convenience
    return JSONResponse({**report, "markdown": renderer.to_markdown(report)})
