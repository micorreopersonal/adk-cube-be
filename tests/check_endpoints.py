from app.api.routes import api_router

endpoints = [route.path for route in api_router.routes]
print("Endpoints registrados:")
for e in sorted(endpoints):
    print(f"  - {e}")

sse_exists = "/executive-report-stream" in endpoints
print(f"\nEndpoint SSE existe: {sse_exists}")

if sse_exists:
    print("✅ Endpoint registrado correctamente")
else:
    print("❌ Endpoint NO registrado")
    print("\nEndpoints que contienen 'executive':")
    exec_endpoints = [e for e in endpoints if 'executive' in e.lower()]
    for e in exec_endpoints:
        print(f"  - {e}")
