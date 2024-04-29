FROM registry.redhat.io/rhel9/rhel-bootc:9.4 as builder

RUN dnf install -y make git kernel-devel-${KERNEL_VERSION} \
    && mkdir /tmp/habanalabs \
    && cd /tmp/habanalabs \
    && rpm2cpio habanalabs-${DRIVER_VERSION}.el${OS_VERSION_MAJOR}.noarch.rpm | cpio -id \
    && rpm2cpio habanalabs-firmware-${DRIVER_VERSION}.el${OS_VERSION_MAJOR}.${TARGET_ARCH}.rpm | cpio -id \
    && cd ./usr/src/habanalabs-${DRIVER_VERSION} \
    && make -j$(nproc) KVERSION="${KERNEL_VERSION}.${TARGET_ARCH}" GIT_SHA=$(cat dkms.conf | grep "KMD_LAST_GIT_SHA=" | cut -d "=" -f 2) \
    && xz drivers/accel/habanalabs/habanalabs.ko \
    && cp /tmp/habanalabs/usr/src/habanalabs-${DRIVER_VERSION}/drivers/accel/habanalabs/habanalabs.ko.xz /tmp/habanalabs.ko.xz

FROM registry.redhat.io/rhel9/rhel-bootc:9.4

ARG KERNEL_VERSION=''

COPY --from=builder --chown=0:0 /tmp/habanalabs/lib/firmware/habanalabs/gaudi /lib/firmware/habanalabs/gaudi
COPY --from=builder --chown=0:0 /tmp/habanalabs.ko.xz /tmp/habanalabs.ko.xz

RUN mv /tmp/habanalabs.ko.xz /lib/modules/${KERNEL_VERSION}.${TARGET_ARCH}/extra/habanalabs.ko.xz \
    && chown root:root /lib/modules/${KERNEL_VERSION}.${TARGET_ARCH}/extra/habanalabs.ko.xz \
    && depmod -a ${KERNEL_VERSION}.${TARGET_ARCH}

ARG RECIPE=parasol
ARG MODEL_IMAGE=quay.io/ai-lab/granite-7b-lab:latest
ARG APP_IMAGE=quay.io/ai-lab/${RECIPE}:latest
ARG SERVER_IMAGE=quay.io/ai-lab/llamacpp_python:latest

# Add quadlet files to setup system to automatically run AI application on boot
COPY build/${RECIPE}.kube build/${RECIPE}.yaml /usr/share/containers/systemd
