
import gc
import sys

def force_garbage_collection():
    print(f"Objetos rastreados antes de GC: {len(gc.get_objects())}")
    n = gc.collect()
    print(f"Desperdicios inalcanzables recolectados: {n}")
    print(f"Objetos rastreados despues de GC: {len(gc.get_objects())}")

if __name__ == "__main__":
    force_garbage_collection()
