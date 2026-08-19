FROM python:3.12-slim
WORKDIR /app
COPY requirements-full.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-full.txt
COPY . .
CMD ["python", "scripts/govern.py", "--ci"]
