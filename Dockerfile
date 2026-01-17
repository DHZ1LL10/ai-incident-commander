# 1. Usamos una imagen base de Python ligera (Slim)
# Es como instalar un Linux chiquito que solo tiene Python 3.11
FROM python:3.11-slim

# 2. Evitamos que Python genere archivos .pyc (basura)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Creamos una carpeta de trabajo dentro del contenedor
WORKDIR /app

# 4. Copiamos SOLO los requerimientos primero (para aprovechar caché)
COPY requirements.txt .

# 5. Instalamos las dependencias dentro del contenedor
RUN pip install --no-cache-dir -r requirements.txt

# 6. Ahora sí, copiamos todo nuestro código fuente
COPY src/ ./src

# 7. Exponemos el puerto 8000 (donde escucha FastAPI)
EXPOSE 8000

# 8. El comando para encender el servidor cuando arranque el contenedor
# Nota: Usamos "0.0.0.0" para que acepte conexiones desde fuera del contenedor
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]