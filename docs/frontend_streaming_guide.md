# Guía de Implementación Frontend: Streaming Progresivo (SSE)

El backend ya está emitiendo los datos en tiempo real mediante **Server-Sent Events (SSE)**. Para que el usuario vea el efecto de "carga progresiva", el frontend **NO** debe esperar a que termine la petición. Debe consumir los eventos a medida que llegan.

## Opción 1: Usando `fetch` (Recomendado para Vue/React/SPA)

Como necesitas enviar el `Authorization: Bearer token`, la API nativa `EventSource` no soporta headers fácilmente (polyfills requeridos). Lo mejor es usar `fetch` y leer el `body` como stream.

### Ejemplo Moderno (JS)

```javascript
async function fetchExecutiveReportStream(period, token) {
  const response = await fetch(\`http://localhost:8080/api/executive-report-stream?period=\${period}\`, {
    method: 'POST',
    headers: {
      'Authorization': \`Bearer \${token}\`,
      'Content-Type': 'application/json'
    },
    // body: JSON.stringify({...}) // Si necesitas body
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let accumulatedData = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    accumulatedData += chunk;

    // Procesar líneas SSE (data: {...})
    const lines = accumulatedData.split('\\n\\n');
    accumulatedData = lines.pop(); // Guardar remanente incompleto

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const jsonStr = line.replace('data: ', '');
        try {
          const sectionData = JSON.parse(jsonStr);
          
          if (sectionData.section_id === 'complete') {
             console.log("✅ Reporte terminado");
             break;
          }
          
          // CRÍTICO: Aquí actualizas el estado de tu UI
          // appendSectionToUI(sectionData);
          console.log("📦 Nueva Sección Recibida:", sectionData.section_id);
          
        } catch (e) {
          console.error("Error parsing SSE JSON", e);
        }
      }
    }
  }
}
```

## Opción 2: Streamlit (Python) - Ejemplo Completo

Sí se puede usar streaming en Streamlit. La clave es usar `requests.post(..., stream=True)` y luego `st.write_stream` (o lógica manual) para ir pintando los bloques.

Crea un archivo `streamlit_app.py`:

```python
import streamlit as st
import requests
import json
import time

st.set_page_config(page_title="ADK Executive Report", layout="wide")

st.title("📊 Reporte Ejecutivo en Vivo (SSE Stream)")

# Config
API_URL = "http://localhost:8080"

# Sidebar para Login
with st.sidebar:
    st.header("Autenticación")
    username = st.text_input("Usuario", "ejecutivo")
    password = st.text_input("Password", "123", type="password")
    
    if st.button("Obtener Token"):
        try:
            resp = requests.post(f"{API_URL}/token", data={"username": username, "password": password})
            if resp.status_code == 200:
                st.session_state["token"] = resp.json()["access_token"]
                st.success("Token obtenido!")
            else:
                st.error("Login fallido")
        except Exception as e:
            st.error(f"Error: {e}")

token = st.session_state.get("token")

if token:
    st.divider()
    period = st.text_input("Periodo (YYYYMM o YYYY)", "2025")
    
    if st.button("🚀 Generar Reporte Streaming"):
        # Contenedor principal donde se agregarán las secciones
        report_container = st.container()
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        headers = {"Authorization": f"Bearer {token}"}
        stream_url = f"{API_URL}/api/executive-report-stream?period={period}"
        
        try:
            # 1. Request con stream=True
            with requests.post(stream_url, headers=headers, stream=True) as response:
                response.raise_for_status()
                
                # 2. Iterar línea por línea
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        
                        # 3. Filtrar eventos SSE
                        if decoded_line.startswith("data: "):
                            json_str = decoded_line[6:] # Quitar "data: "
                            try:
                                data = json.loads(json_str)
                                
                                # Actualizar Barra de Progreso
                                if "progress" in data:
                                    progress_bar.progress(data["progress"])
                                
                                section_id = data.get("section_id")
                                
                                # Manejo de Finalización
                                if section_id == "complete":
                                    status_text.success("✅ Generación Completa")
                                    st.balloons()
                                    break
                                    
                                # Manejo de Errores
                                if section_id == "error":
                                    st.error(f"Error Backend: {data.get('error')}")
                                    break
                                
                                # RENDERIZADO DE BLOQUES
                                with report_container:
                                    with st.expander(f"📦 Sección: {section_id.upper()}", expanded=True):
                                        blocks = data.get("blocks", [])
                                        for block in blocks:
                                            b_type = block.get("type")
                                            payload = block.get("payload")
                                            variant = block.get("variant")
                                            
                                            if b_type == "text":
                                                if variant == "h2": st.header(payload)
                                                elif variant == "h3": st.subheader(payload)
                                                elif variant == "insight": st.info(payload, icon="💡")
                                                else: st.write(payload)
                                                
                                            elif b_type == "kpi_row":
                                                # Renderizar KPIs en columnas
                                                cols = st.columns(len(payload))
                                                for idx, kpi in enumerate(payload):
                                                    cols[idx].metric(
                                                        label=kpi.get("label"), 
                                                        value=f"{kpi.get('value'):.1f}",
                                                        delta=kpi.get("delta")
                                                    )
                                            
                                            elif b_type == "table":
                                                st.dataframe(payload.get("rows"))
                                                
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            st.error(f"Error de conexión: {e}")
else:
    st.info("Por favor inicia sesión en la sidebar para continuar.")
```

## Resumen

- **Web (React/Vue):** Usar `fetch` + `reader`.
- **Streamlit:** Usar `requests.post(..., stream=True)` + `response.iter_lines()`.

