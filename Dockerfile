# Stage 1: Build
FROM python:3.12-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install sentence-transformers==3.2.0

# Stage 2: Production
FROM public.ecr.aws/lambda/python:3.12
COPY --from=build /usr/local/lib/python3.12/site-packages ${LAMBDA_TASK_ROOT}
COPY ./app ${LAMBDA_TASK_ROOT}
CMD ["app.handler"]
