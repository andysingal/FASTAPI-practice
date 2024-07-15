FROM python:3.10

WORKDIR /app

# Copy application code
COPY . .

# Clear pip cache
RUN pip cache purge

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

