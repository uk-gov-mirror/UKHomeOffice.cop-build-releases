FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd builds

USER builds

COPY --chown=1000 *.py ./
RUN chmod 755 *.py

ENTRYPOINT ["python", "/usr/src/app/drone_builds.py"]
