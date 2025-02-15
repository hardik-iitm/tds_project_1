# Step 1: Use an official Python runtime as a parent image
FROM python:3.12-slim

# Step 2: Set the working directory in the container
WORKDIR /app

# Step 3: Copy the contents of the local directory into the container
COPY . /app/

# Step 4: Install any dependencies (you should have a requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Expose port 8000 (FastAPI runs on this port by default)
EXPOSE 8000

# Step 6: Run the application with Uvicorn (specify FastAPI app entry point)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
