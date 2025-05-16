ARG IMAGE_WITH_PACKAGES=python-image-with-packages
FROM $IMAGE_WITH_PACKAGES

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "run.py"]