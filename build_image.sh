#!/usr/bin/env sh

#set -ex

function printHelp() {
                echo $(basename $0)" options:";
                echo "    -A <Architectures to use> # Compiling to ${ARCHS} now, examples: amd64 arm64v8 arm32v6 arm32v7"
                [ ${FLAG_UPLOADIMAGES} -gt 0 ] && echo "    -U # Do not upload images - the default is upload the images to the registry";
                [ ${FLAG_UPLOADIMAGES} -eq 0 ] && echo "    -U # Upload images - the default is not to upload the images to the registry";
                [ ${FLAG_UPLOADMANIFEST} -gt 0 ] && echo "    -M # Do not upload manifest - the default is upload the manifest to the registry";
                [ ${FLAG_UPLOADMANIFEST} -eq 0 ] && echo "    -U # Upload manifest - the default is not to upload the manifest to the registry";
                [ ${FLAG_USESQUASH} -gt 0 ] && echo "    -S # Do not squash images - the default is squash the images";
                [ ${FLAG_USESQUASH} -eq 0 ] && echo "    -S # Squash images - the default is not to squash the images";
                echo "    -B <build tag to use> # Default is today's date with seconds UTC";
                echo "    -T <additional build tag to use> # The whole build tag will be added to the -B or the default";
                echo "    -I <add this to the image name>"
                return;
}

BUILD_TAG=$(date -u "+%Y%m%d%H%M%S")
REPOSITORY_NAME="registry.gitlab.com/arm-research/isr/e2e-demo/waggle-plugin_manager"
IMAGE_NAME="image-detector-simple"
DIRECTORY_TO_RUN=.

# Check which host are we running on: Linux or Darwin, also are we crosscompiling?
LINUX_HOST=1
DARWIN_HOST=0
case $(uname -m) in
        x86_64)
                MACHINE_HOST=amd64;
                ;;
        armv7l)
                MACHINE_HOST=arm32v7;
                ;;
        aarch64)
                MACHINE_HOST=arm64v8;
                ;;
        *)
                echo "Unrecognized archuitecture $(uname -m)";
                exit 1;;
esac

if [ $(uname) = "Darwin" ]
then
        LINUX_HOST=0
        DARWIN_HOST=1
fi

# If the user does not change it, these are the architectures we will compile for
ARCHS="arm32v7"

# If the user does not change it the images will be uploaded to the registry
FLAG_UPLOADIMAGES=1
FLAG_UPLOADMANIFEST=1
FLAG_USESQUASH=1

# No changes to the image names
ADDITIONAL_TAG=""
ADDITIONAL_IMAGE_NAME=""

while getopts hA:B:MST:U name
do
        case $name in
        h)
                printHelp;
                exit 0;;
        A)
                ARCHS="$OPTARG";;
        U)
                [ ${FLAG_UPLOADIMAGES} -gt 0 ] && FLAG_UPLOADIMAGES=0;
                [ ${FLAG_UPLOADIMAGES} -eq 0 ] && FLAG_UPLOADIMAGES=1;
                ;;
        M)
                [ ${FLAG_UPLOADMANIFEST} -gt 0 ] && FLAG_UPLOADMANIFEST=0;
                [ ${FLAG_UPLOADMANIFEST} -eq 0 ] && FLAG_UPLOADMANIFEST=1;
                ;;
        S)
                [ ${FLAG_USESQUASH} -gt 0 ] && FLAG_USESQUASH=0;
                [ ${FLAG_USESQUASH} -eq 0 ] && FLAG_USESQUASH=1;
                ;;
        B)
                BUILD_TAG="$OPTARG";;
        T)
                ADDITIONAL_TAG="$OPTARG";;
        I)
                ADDITIONAL_IMAGE_NAME="$OPTARG";;
        *)
                printHelp;
                exit 0;
                ;;
        esac
done

# We need docker to support manifest for multiarch, try so see if we have it
if [ ${FLAG_UPLOADMANIFEST} -gt 0 ]
then
        if [ -e ~/.docker/config.json ]
        then
                grep -i "experimental.*:.*enabled" ~/.docker/config.json 2>/dev/null || sed -i -e 's/^{/{\n    "experimental":"enabled",/' ~/.docker/config.json
        else
                mkdir -p ~/.docker
                cat <<EOF  > ~/.docker/config.json
{
        "experimental":"enabled"
}
EOF
        fi
fi
CURDIR=$(dirname $0)
cd "${CURDIR}"
BUILD_TAG="${BUILD_TAG}${ADDITIONAL_TAG}"
USE_SQUASH=""
if [ ${FLAG_USESQUASH} -gt 0 ]
then
        USE_SQUASH="--squash"
fi

if [ ! -z "${REPOSITORY_NAME}" ]
then
        REPOSITORY_NAME="${REPOSITORY_NAME}/"
fi

PREVDIR=$(pwd)

cd ${DIRECTORY_TO_RUN}

IMAGES_ADD_MANIFEST=""

for ARCH_TO_COMPILE in ${ARCHS}
do
        QEMU_ADD=""
        QEMU_REM=""
        ARCH=""
        ARCH_TAG=""
        ARCH_LIBDIR=""
        ARCH_DOCKER=""
        case ${ARCH_TO_COMPILE} in
                noarch)
                        GOARCH=""
                        ;;
                amd64)
                        GOARCH="amd64"
                        ARCH_TAG="-${ARCH_TO_COMPILE}"
                        ARCH_LIBDIR="x86_64-linux-gnu"
                        ARCH_DOCKER="amd64"
                        ;;
                arm32v7)
                        GOARCH="armv6l"
                        ARCH=${ARCH_TO_COMPILE}"/"
                        if [ ${DARWIN_HOST} -eq 0 -a ! ${MACHINE_HOST} = ${ARCH_TO_COMPILE} ]
                        then
                                cp /usr/bin/qemu-arm-static qemu-arm-static
                                QEMU_ADD="COPY qemu-arm-static /usr/bin/"
                                QEMU_REM="RUN rm /usr/bin/qemu-arm-static"
                        fi
                        ARCH_TAG="-${ARCH_TO_COMPILE}"
                        ARCH_LIBDIR="arm-linux-gnueabihf"
                        ARCH_DOCKER="arm"
                        ;;
                arm64v8)
                        GOARCH="arm64"
                        ARCH=${ARCH_TO_COMPILE}"/"
                        if [ ${DARWIN_HOST} -eq 0 -a ! ${MACHINE_HOST} = ${ARCH_TO_COMPILE} ]
                        then
                                cp /usr/bin/qemu-aarch64-static qemu-aarch64-static
                                QEMU_ADD="COPY qemu-aarch64-static /usr/bin/"
                                QEMU_REM="RUN rm /usr/bin/qemu-aarch64-static"
                        fi
                        ARCH_TAG="-${ARCH_TO_COMPILE}"
                        ARCH_LIBDIR="aarch64-linux-gnu"
                        ARCH_DOCKER="arm64"
                        ;;
        esac

        IMAGE_TO_CREATE="${REPOSITORY_NAME}${IMAGE_NAME}${ARCH_TAG}${ADDITIONAL_IMAGE_NAME}:${BUILD_TAG}"

        sed -e "s|ARCHITECTURE_TO_COMPILE|${ARCH}|g" \
            -e "s|GOARCH|${GOARCH}|g" \
            -e "s|QEMU_ADD|${QEMU_ADD}|g" \
            -e "s|QEMU_REM|${QEMU_REM}|g" \
            -e "s|ARCH_LIBDIR|${ARCH_LIBDIR}|g" \
            "${PREVDIR}"/Dockerfile.template > Dockerfile

        docker build ${USE_SQUASH} -t "${IMAGE_TO_CREATE}" . || exit -1

        IMAGES_ADD_MANIFEST="${IMAGES_ADD_MANIFEST}"$(echo "${ARCH_DOCKER}" "${IMAGE_TO_CREATE}")
done

MANIFEST_NAME="${REPOSITORY_NAME}${IMAGE_NAME}${ADDITIONAL_IMAGE_NAME}:${BUILD_TAG}"

# If we are pushing the images to the registry
if [ $FLAG_UPLOADIMAGES -gt 0 ]
then
        echo "${IMAGES_ADD_MANIFEST}" | while read ARCH IMAGES_TO_PUSH
        do
                docker push ${IMAGES_TO_PUSH} || exit -1
        done

        if [ $FLAG_UPLOADMANIFEST -gt 0 ]
        then
                rm -rf ~/.docker/manifests/*

                IMAGES_MANIFEST=$(echo "${IMAGES_ADD_MANIFEST}" | while read ARCH IMAGES_TO_PUSH
                do
                        echo ${IMAGES_TO_PUSH}
                done)

                docker manifest create --insecure "${MANIFEST_NAME}" ${IMAGES_MANIFEST} || exit -1

                echo "${IMAGES_ADD_MANIFEST}" | while read ARCH IMAGES_TO_PUSH
                do
                        docker manifest annotate --arch $ARCH "${MANIFEST_NAME}" "${IMAGES_TO_PUSH}"
                done

                docker manifest push --insecure "${MANIFEST_NAME}"
        fi
fi

exit 0
