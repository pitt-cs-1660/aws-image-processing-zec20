FROM public.ecr.aws/lambda/python:3.13

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

############
#
# TODO: implement the rest of the image
#
############
WORKDIR /var/task

COPY pyproject.toml ./

RUN uv sync --no-dev

COPY handler.py .

ENV PYTHONPATH="/var/task/.venv/lib/python3.13/site-packages"

CMD ["handler.greyscale_handler"]