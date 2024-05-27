# Use the official Python base image from Docker Hub
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install the required Python packages, including Streamlit
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# Copy the rest of the application files into the container
COPY . .

# Expose the port Streamlit runs on (default is 8501)
EXPOSE 8501

# Set the command to run your Streamlit app
# Replace "your_app.py" with the name of your Streamlit app
CMD ["streamlit", "run", "metacog.py"]
