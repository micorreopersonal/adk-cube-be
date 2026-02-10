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

class ReportInsightGenerator:
    """
    Generates AI-powered narratives for the Executive Report using the Semantic Cube context.
    Includes persistent caching (Firestore) and retry logic (Tenacity).
    """
    
    def __init__(self):
        settings = get_settings()
        try:
            self.client = Client(
                vertexai=settings.GOOGLE_GENAI_USE_VERTEXAI,
                project=settings.PROJECT_ID,
                location=settings.REGION
            )
            self.model_name = "gemini-2.0-flash-exp" # Or configured model
            
            # Initialize Synchronous Firestore for Cache
            # We use a separate collection 'ai_insights_cache'
            # Note: Project ID is picked up from env or default creds
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
        """Check if insight exists in Firestore cache and is valid (e.g. < 7 days old)."""
        if not self.db: return None
        
        try:
            doc_ref = self.cache_collection.document(key)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                # Optional: Check TTL. For now, we assume valid if exists.
                # If we wanted 7 day TTL:
                # created_at = data.get('created_at')
                # if created_at and (datetime.now(created_at.tzinfo) - created_at).days > 7: return None
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
        stop=stop_after_attempt(5),  # Increased from 3 to 5 attempts
        wait=wait_exponential(multiplier=2, min=5, max=60),  # Increased from max=10 to max=60
        reraise=True
    )
    def _generate_with_retry(self, prompt: str, max_tokens: int) -> str:
        """
        Internal generation with retry logic for 429 Quota Exceeded.
        Retries up to 5 times with exponential backoff (5s, 10s, 20s, 40s, 60s).
        """
        logger.info("🔄 Attempting AI insight generation...")
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=max_tokens
            )
        )
        return response.text.strip()

    def _generate(self, prompt: str, max_tokens: int = 150) -> str:
        if not self.client:
            return "[AI Narrative Unavailable - Client Error]"

        # 1. Check Cache
        cache_key = self._get_cache_key(prompt)
        cached_content = self._check_cache(cache_key)
        if cached_content:
            logger.info(f"✨ Insight Cache Hit! (Key: {cache_key[:8]}...)")
            return cached_content

        # 2. Generate with Retry
        try:
            content = self._generate_with_retry(prompt, max_tokens)
            
            # 3. Save Cache
            self._save_cache(cache_key, content)
            return content
            
        except google.api_core.exceptions.ResourceExhausted:
            logger.error("❌ Quota exceeded after retries.")
            return "[AI Narrative Unavailable - Quota Exceeded]"
        except Exception as e:
            logger.error(f"Error generating insight: {e}")
            return "[AI Narrative Unavailable]"

    def generate_report_narratives(self, snapshot: Dict[str, Any], period_display: str) -> Dict[str, str]:
        """
        Receives the full snapshot (results from all blocks) and generates 
        a coherent set of narratives for each section plus a conclusion.
        """
        # 0. Contextualize the prompt with ALL data summary
        # We'll create a summarized view of all data to fit in prompt
        all_data_summary = ""
        for key, res in snapshot.items():
            content_sample = str(res.get("content", []))[:500]
            all_data_summary += f"\n### BLOQUE: {key}\n{content_sample}\n"

        prompt = f"""
        Actúa como un Director de RRHH (CHRO) analizando el Reporte Ejecutivo de {period_display}.
        
        A continuación tienes los DATOS CRUDOS de todos los bloques del reporte:
        {all_data_summary}
        
        TU TAREA: Generar un objeto JSON con las siguientes claves de narrativa (en español):
        1. "critical_insight": Un párrafo inicial (max 60 palabras) que cruce los datos más impactantes.
        2. "segmentation": Análisis breve de FFVV vs Admins (max 40 palabras).
        3. "voluntary_trend": Análisis de la tasa voluntaria y causas (max 50 palabras).
        4. "talent_leakage": Alerta sobre bajas HiPo/HiPer (max 40 palabras).
        5. "strategic_conclusion": Síntesis del estado de salud de la organización (max 50 palabras).
        6. "recommendations": Lista de 2-3 ACCIONES TÁCTICAS y EDITORIALES. No uses obviedades. Usa tu expertise en People Analytics para sugerir intervenciones precisas (ej: "Revisar bandas salariales en FFVV", "Mentoring para HiPos"). Max 80 palabras.
        
        REGLA DE ORO: La narrativa debe ser COHERENTE. Si hay mucha rotación en FFVV, la recomendación debe ir dirigida a FFVV.
        
        RETORNA UNICAMENTE UN JSON PURO.
        """

        try:
            response_text = self._generate(prompt, max_tokens=1200)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            raise ValueError("No JSON found in response")
        except Exception as e:
            logger.warning(f"Complex holistic generation failed ({e}). Retrying with simplified strategy...")
            # Fallback: Generate just a text summary and fill the rest with placeholders
            simple_prompt = f"""
            Analiza estos datos de RRHH y dame 2 recomendaciones estratégicas breves:
            {all_data_summary[:3000]}
            """
            try:
                fallback_text = self._generate(simple_prompt, max_tokens=200)
                return {
                    "critical_insight": "Resumen generado en modo simple.",
                    "strategic_conclusion": "Se requiere análisis manual por error en generación compleja.",
                    "segmentation": "Ver gráfico.",
                    "voluntary_trend": "Ver gráfico.",
                    "talent_leakage": "Ver tabla.",
                    "recommendations": fallback_text
                }
            except:
                return {}
