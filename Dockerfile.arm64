FROM registry.gitlab.com/arm-research/smarter/jetpack-triton:arm64_client_base as base


FROM debian:bullseye-20200720-slim

# Ensure apt won't prompt for selecting options
ENV DEBIAN_FRONTEND=noninteractive

COPY --from=base /workspace/install/python/tritonhttpclient-2.1.0.dev0-py3-none-any.whl tritonhttpclient-2.1.0.dev0-py3-none-any.whl
COPY --from=base /workspace/install/python/tritongrpcclient-2.1.0.dev0-py3-none-any.whl tritongrpcclient-2.1.0.dev0-py3-none-any.whl
COPY --from=base /workspace/install/python/tritonclientutils-2.1.0.dev0-py3-none-any.whl tritonclientutils-2.1.0.dev0-py3-none-any.whl

RUN apt update && apt install -yqq --no-install-recommends \
        curl \
        python3-pip \
        python3-dev \
        build-essential \
        pkg-config \
        python3-numpy \
        python3-grpcio \
        libhdf5-dev \
        python3-opencv \
        python3-flask \
	libffi-dev \
	libssl-dev \
        python3-paho-mqtt && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade \
        wheel \
        setuptools \
        tritonhttpclient-2.1.0.dev0-py3-none-any.whl \
        tritongrpcclient-2.1.0.dev0-py3-none-any.whl \
        tritonclientutils-2.1.0.dev0-py3-none-any.whl

COPY *.py *.classes ./
COPY templates /templates

CMD [ "bash" ]