from typing import Dict, Any, List, Optional
import os
import logging
import hashlib
import json
import re
from datetime import datetime, timedelta
from google.genai import types, Client
from google.cloud import firestore
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import google.api_core.exceptions

from app.core.config.config import get_settings

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> Optional[Dict]:
    """
    Robustly extracts JSON from LLM responses that may include markdown fences,
    preamble text, truncation, or other wrapping.
    """
    # 1. Strip markdown code fences if present
    cleaned = re.sub(r'```(?:json)?\s*', '', text)
    cleaned = cleaned.strip()

    # 2. Try direct parse first (best case: clean JSON)
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # 3. Extract the outermost { ... } block
    brace_match = re.search(r'\{[\s\S]*\}', cleaned)
    if brace_match:
        try:
            result = json.loads(brace_match.group(0))
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # 4. Handle truncated JSON — try to repair by closing open strings/braces
    # Find the start of JSON
    start_idx = cleaned.find('{')
    if start_idx >= 0:
        json_fragment = cleaned[start_idx:]
        # Try progressively adding closing characters
        for suffix in ['"}', '"}]}', '"}]}'  , '"}'  '}']:
            try:
                result = json.loads(json_fragment + suffix)
                if isinstance(result, dict):
                    logger.warning(f"Repaired truncated JSON with suffix: {suffix}")
                    return result
            except (json.JSONDecodeError, ValueError):
                continue

    return None


def _clean_markdown(obj):
    """Recursively strip markdown formatting (**, *, #) from string values."""
    if isinstance(obj, str):
        cleaned = obj.replace('**', '').replace('*', '').strip()
        # Remove leading markdown headers
        cleaned = re.sub(r'^#+\s*', '', cleaned)
        return cleaned
    if isinstance(obj, dict):
        return {k: _clean_markdown(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_markdown(item) for item in obj]
    return obj


def _summarize_snapshot(snapshot: Dict[str, Any]) -> str:
    """
    Converts raw snapshot blocks into a clean, LLM-readable summary.
    Extracts actual data values instead of dumping Python repr().
    Handles both Pydantic-serialized types (KPI_ROW, CHART, TABLE) and lowercase variants.
    """
    parts = []
    for key, res in snapshot.items():
        block_lines = [f"### BLOQUE: {key}"]
        summary = res.get("summary", "")
        if summary:
            block_lines.append(f"Resumen: {summary}")

        content = res.get("content", [])
        for item in content:
            if not isinstance(item, dict):
                continue
            # Normalize type to uppercase for consistent matching
            item_type = item.get("type", "").upper()

            if item_type == "KPI_ROW":
                payload = item.get("payload", [])
                for kpi in payload:
                    if isinstance(kpi, dict):
                        label = kpi.get("label", "")
                        value = kpi.get("value", "N/A")
                        tooltip = kpi.get("tooltip", "")
                        line = f"- {label}: {value}"
                        if tooltip:
                            line += f" ({tooltip})"
                        block_lines.append(line)

            elif item_type == "CHART":
                payload = item.get("payload", {})
                labels = payload.get("labels", [])
                datasets = payload.get("datasets", [])
                chart_meta = item.get("metadata", {})
                title = chart_meta.get("title", "")
                if title:
                    block_lines.append(f"  Gráfico: {title}")
                for ds in datasets:
                    if isinstance(ds, dict):
                        ds_label = ds.get("label", "Serie")
                        data = ds.get("data", [])
                        pairs = [f"{l}={v}" for l, v in zip(labels, data) if v is not None]
                        block_lines.append(f"- {ds_label}: {', '.join(pairs[:12])}")

            elif item_type == "TABLE":
                payload = item.get("payload", {})
                rows = payload.get("rows", [])
                if rows:
                    block_lines.append(f"- Tabla con {len(rows)} registros")
                    for row in rows[:5]:
                        if isinstance(row, dict):
                            vals = [f"{k}={v}" for k, v in list(row.items())[:6]]
                            block_lines.append(f"  {', '.join(vals)}")
                else:
                    block_lines.append("- Tabla sin datos")

            elif item_type == "TEXT":
                text_payload = item.get("payload", "")
                if text_payload and item.get("variant") != "h2" and item.get("variant") != "h3":
                    block_lines.append(f"- {text_payload}")

        # Only add block if it has data beyond the header
        if len(block_lines) > 1:
            parts.append("\n".join(block_lines))
        else:
            parts.append(f"### BLOQUE: {key}\n- Sin datos disponibles")

    result = "\n\n".join(parts)
    logger.debug(f"Snapshot summary for LLM (first 500 chars): {result[:500]}")
    return result

    return "\n\n".join(parts)


class ReportInsightGenerator:
    """
    Generates AI-powered narratives for the Executive Report using the Semantic Cube context.
    Includes persistent caching (Firestore) and retry logic (Tenacity).
    """

    # Cache TTL in days — entries older than this are considered stale
    CACHE_TTL_DAYS = 7

    def __init__(self):
        settings = get_settings()
        try:
            self.client = Client(
                vertexai=settings.GOOGLE_GENAI_USE_VERTEXAI,
                project=settings.PROJECT_ID,
                location=settings.REGION
            )
            self.model_name = settings.MODEL_NAME or "gemini-2.5-flash"

            self.db = firestore.Client(project=os.getenv("PROJECT_ID"))
            self.cache_collection = self.db.collection("ai_insights_cache")

        except Exception as e:
            logger.error(f"Failed to initialize AI/DB client: {e}")
            self.client = None
            self.db = None

    def _get_cache_key(self, prompt: str) -> str:
        """Generate a deterministic hash for the prompt."""
        return hashlib.sha256(prompt.encode('utf-8')).hexdigest()

    def _check_cache(self, key: str) -> Optional[str]:
        """Check if insight exists in Firestore cache and is within TTL."""
        if not self.db: return None

        try:
            doc_ref = self.cache_collection.document(key)
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                created_at = data.get('created_at')
                if created_at:
                    age = datetime.now(created_at.tzinfo) - created_at
                    if age.days > self.CACHE_TTL_DAYS:
                        logger.info(f"Cache expired for key {key[:8]}... (age: {age.days}d)")
                        return None
                return data.get('content')
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")

        return None

    def _save_cache(self, key: str, content: str):
        """Save insight to Firestore cache."""
        if not self.db: return

        try:
            doc_ref = self.cache_collection.document(key)
            doc_ref.set({
                'content': content,
                'created_at': firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

    @retry(
        retry=retry_if_exception_type(google.api_core.exceptions.ResourceExhausted),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=5, max=60),
        reraise=True
    )
    def _generate_with_retry(self, prompt: str, max_tokens: int, response_mime_type: Optional[str] = None) -> str:
        """
        Internal generation with retry logic for 429 Quota Exceeded.
        Optionally forces JSON response_mime_type for structured output.
        """
        logger.info("Attempting AI insight generation...")
        config = types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=max_tokens
        )
        if response_mime_type:
            config = types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=max_tokens,
                response_mime_type=response_mime_type
            )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config
        )
        return response.text.strip()

    def _generate(self, prompt: str, max_tokens: int = 150, response_mime_type: Optional[str] = None) -> str:
        if not self.client:
            return "[AI Narrative Unavailable - Client Error]"

        # 1. Check Cache
        cache_key = self._get_cache_key(prompt)
        cached_content = self._check_cache(cache_key)
        if cached_content:
            logger.info(f"Insight Cache Hit! (Key: {cache_key[:8]}...)")
            return cached_content

        # 2. Generate with Retry
        try:
            content = self._generate_with_retry(prompt, max_tokens, response_mime_type)

            # 3. Save Cache
            self._save_cache(cache_key, content)
            return content

        except google.api_core.exceptions.ResourceExhausted:
            logger.error("Quota exceeded after retries.")
            return "[AI Narrative Unavailable - Quota Exceeded]"
        except Exception as e:
            logger.error(f"Error generating insight: {e}")
            return "[AI Narrative Unavailable]"

    def generate_report_narratives(self, snapshot: Dict[str, Any], period_display: str) -> Dict[str, str]:
        """
        Receives the full snapshot (results from all blocks) and generates
        a coherent set of narratives for each section plus a conclusion.
        """
        # Build a clean, structured data summary (not raw Python repr)
        all_data_summary = _summarize_snapshot(snapshot)
        logger.info(f"[NARRATIVE] Data summary for LLM ({len(all_data_summary)} chars):\n{all_data_summary[:1000]}")

        prompt = f"""Eres un CHRO analizando el Reporte Ejecutivo de {period_display}.

DATOS:
{all_data_summary}

Genera JSON con estas claves (en español, texto plano SIN markdown ni asteriscos):
- "critical_insight": Párrafo cruzando datos impactantes (max 50 palabras)
- "segmentation": FFVV vs Admins (max 30 palabras)
- "voluntary_trend": Rotación voluntaria vs involuntaria (max 40 palabras)
- "talent_leakage": Bajas HiPo/HiPer o "Sin fuga critica" (max 30 palabras)
- "strategic_conclusion": Estado de salud organizacional (max 40 palabras)
- "recommendations": Array de 2-3 strings con acciones tacticas especificas (max 20 palabras cada una)

IMPORTANTE: Texto plano sin formato. No uses ** ni * ni # ni markdown. El campo recommendations debe ser un array JSON de strings."""

        try:
            response_text = self._generate(prompt, max_tokens=2048, response_mime_type="application/json")
            logger.info(f"Narrative raw response (first 300 chars): {response_text[:300]}")

            # Robust JSON extraction (handles markdown fences, preamble, etc.)
            parsed = _extract_json(response_text)
            if parsed and isinstance(parsed, dict):
                # Strip markdown formatting from all string values
                parsed = _clean_markdown(parsed)
                # Validate we got at least the critical keys
                expected_keys = {"critical_insight", "strategic_conclusion", "recommendations"}
                if expected_keys.intersection(parsed.keys()):
                    return parsed
                logger.warning(f"JSON parsed but missing expected keys. Got: {list(parsed.keys())}")

            logger.warning(f"Failed to extract valid JSON from narrative response. Raw: {response_text[:500]}")
            raise ValueError("No valid JSON structure found in response")

        except Exception as e:
            logger.warning(f"Complex holistic generation failed ({e}). Falling back to per-section strategy...")
            return self._generate_per_section_fallback(all_data_summary, period_display)

    def _generate_per_section_fallback(self, data_summary: str, period_display: str) -> Dict[str, str]:
        """
        Fallback: generate each narrative section independently.
        More resilient than a single monolithic call.
        """
        sections = {
            "critical_insight": f"Analiza estos datos de RRHH de {period_display} y genera UN párrafo de insight crítico (max 60 palabras, en español):\n{data_summary[:2000]}",
            "segmentation": f"Analiza brevemente la rotación de FFVV vs Administrativos (max 40 palabras, en español):\n{data_summary[:1500]}",
            "voluntary_trend": f"Analiza brevemente la tendencia de rotación voluntaria vs involuntaria (max 50 palabras, en español):\n{data_summary[:1500]}",
            "talent_leakage": f"Analiza si hay fuga de talento HiPo/HiPer (max 40 palabras, en español). Si no hay datos, indica que no hay fuga crítica:\n{data_summary[:1500]}",
            "strategic_conclusion": f"Da una conclusión estratégica sobre el estado de salud organizacional (max 50 palabras, en español):\n{data_summary[:2000]}",
            "recommendations": f"Sugiere 2-3 acciones tácticas precisas basadas en estos datos de RRHH (max 80 palabras, en español):\n{data_summary[:2000]}",
        }

        result = {}
        for key, section_prompt in sections.items():
            try:
                text = self._generate(section_prompt, max_tokens=200)
                # Skip responses that indicate generation failure
                if text.startswith("[AI Narrative"):
                    result[key] = ""
                else:
                    result[key] = text
            except Exception as e:
                logger.warning(f"Per-section fallback failed for '{key}': {e}")
                result[key] = ""

        return result
