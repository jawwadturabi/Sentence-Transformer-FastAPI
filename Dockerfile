# Define custom function directory
ARG FUNCTION_DIR="/function"

##############################
# Stage 1: Build Image
##############################
FROM python:3.12 AS build-image

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Set environment variables for caching
ENV HF_HOME=/tmp/huggingface

# Create cache directories with appropriate permissions
RUN mkdir -p ${HF_HOME}/cache && chmod -R 777 /tmp

# Create function directory
RUN mkdir -p ${FUNCTION_DIR}

COPY requirements.txt ${FUNCTION_DIR}
# Install the function's dependencies including awslambdaric and sentence-transformers
RUN pip install --no-cache-dir -r ${FUNCTION_DIR}/requirements.txt -t ${FUNCTION_DIR} \
&& pip install --no-cache-dir sentence-transformers==3.2.0 -t ${FUNCTION_DIR}

# Copy function code
COPY ./app ${FUNCTION_DIR}
# Pre-download the SentenceTransformer model to cache
# RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2', cache_folder='${TRANSFORMERS_CACHE}')"

##############################
# Stage 2: Final Image
##############################
FROM python:3.12-slim

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Set environment variables for caching
ENV HF_HOME=/tmp/huggingface

# Create cache directories with appropriate permissions
RUN mkdir -p ${HF_HOME}/cache && chmod -R 777 /tmp

# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}

# Copy built dependencies and cached models from build stage
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

# Install AWS Lambda Runtime Interface Client
RUN pip install --no-cache-dir awslambdaric

# Set runtime interface client as default command for the container runtime
ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]

# Pass the name of the function handler as an argument to the runtime
CMD [ "app.handler" ]
