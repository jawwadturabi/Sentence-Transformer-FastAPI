FROM public.ecr.aws/lambda/python:3.10

# Copy only the requirements.txt file first to leverage Docker caching
COPY requirements.txt .

# Install dependencies based on requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Now copy the rest of the application code
COPY ./app ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD [ "app.handler" ]