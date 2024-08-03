# Use the official Python image as the base image
FROM python:3.12.3-slim

# Set the working directory inside the container
WORKDIR /app/kasa_collector

# Copy the requirements file and other application files into the container
COPY requirements.txt ./src/config.py ./src/influxdb_storage.py ./src/kasa_collector.py ./src/kasa_api.py  ./

# Upgrade pip and install required packages
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Run your Python script
CMD ["python3", "./kasa_collector.py"]
