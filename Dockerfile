FROM python:3.8

WORKDIR /main_app


RUN apt update && \
    apt install -y git wget ffmpeg libsm6 libxext6 

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu121



COPY cache_dir /main_app/cache_dir
COPY utils /main_app/utils
COPY LanguageBind /main_app/LanguageBind

COPY .env .
COPY generate_key.pyc .
COPY app.pyc .
COPY config.pyc .
COPY db_utils.pyc .
COPY languagebind_utils.pyc .


# Create symlink for Faiss
RUN cd /usr/local/lib/python3.8/site-packages/faiss && \
    ln -s swigfaiss.py swigfaiss_avx2.py

WORKDIR /main_app


EXPOSE 5800

# Cloud license management – customers must supply these at runtime:
#   docker run -e LICENSE_KEY="<token>" -e LICENSE_SERVER_URL="https://your-project.vercel.app" ...
ENV LICENSE_KEY=""
ENV LICENSE_SERVER_URL=""

ENTRYPOINT ["python", "app.pyc"]
# ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "myenv", "python", "app.pyc"]

CMD ["--working_dir", "/work_dir", "--batch_size", "32", "--port", "5800", "--database_url", "sqlite:///work_dir/video_search.db"]
