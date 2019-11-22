#!/usr/bin/env sh

set -ex

BUILD_TAG=$(date -u "+%Y%m%d%H%M%S")
REPOSITORY_NAME="registry.gitlab.com/arm-research/isr/e2e-demo/waggle-plugin_manager"
IMAGE_NAME="image-detector-simple"
DIRECTORY_TO_RUN=.

# If the user does not change it, these are the architectures we will compile for
ARCHS="arm32v7"

# If the user does not change it the images will be uploaded to the registry
FLAG_UPLOADIMAGES=1
FLAG_UPLOADMANIFEST=1

# No changes to the image names
ADDITIONAL_TAG=""
ADDITIONAL_IMAGE_NAME=""

while getopts A:B:MST:U name
do
        case $name in
        A)
            ARCHS="$OPTARG";;
        U)
            FLAG_UPLOADIMAGES=0;;
        M)
            FLAG_UPLOADMANIFEST=0;;
        B)
            BUILD_TAG="$OPTARG";;
        T)
            ADDITIONAL_TAG="$OPTARG";;
        I)
            ADDITIONAL_IMAGE_NAME="$OPTARG";;
        *)
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

BUILD_TAG_OLD="${BUILD_TAG}${ADDITIONAL_TAG}"

cd ${DIRECTORY_TO_RUN}

IMAGES_ADD_MANIFEST=""

for ARCH_TO_COMPILE in ${ARCHS}
do
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
                        ARCH_TAG="-${ARCH_TO_COMPILE}"
                        ARCH_LIBDIR="arm-linux-gnueabihf"
                        ARCH_DOCKER="arm"
                        ;;
                arm64v8)
                        GOARCH="arm64"
                        ARCH=${ARCH_TO_COMPILE}"/"
                        ARCH_TAG="-${ARCH_TO_COMPILE}"
                        ARCH_LIBDIR="aarch64-linux-gnu"
                        ARCH_DOCKER="arm64"
                        ;;
        esac

        IMAGE_OLD="${REPOSITORY_NAME}/${IMAGE_NAME}${ARCH_TAG}${ADDITIONAL_IMAGE_NAME}:${BUILD_TAG_OLD}"
        IMAGE_TO_CREATE="${REPOSITORY_NAME}/${IMAGE_NAME}${ARCH_TAG}${ADDITIONAL_IMAGE_NAME}:${BUILD_TAG}"

        docker pull "${IMAGE_OLD}" || exit 1
        docker tag "${IMAGE_OLD}" "${IMAGE_TO_CREATE}" || exit 1

        IMAGES_ADD_MANIFEST="${IMAGES_ADD_MANIFEST}"$(echo "${ARCH_DOCKER}" "${IMAGE_TO_CREATE}")
done

MANIFEST_NAME="${REPOSITORY_NAME}/${IMAGE_NAME}${ADDITIONAL_IMAGE_NAME}:${BUILD_TAG}"

# If we are pushing the images to the registry
if [ $FLAG_UPLOADIMAGES -gt 0 ]
then
        for IMAGES_TO_PUSH in ${IMAGES_ADD_MANIFEST}
        do
                docker push ${IMAGES_TO_PUSH} || exit 1
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

# Update the yaml using the template
#sed -e "s|IMAGE_NAME|${MANIFEST_NAME}|g" ../argus-device-manager.yaml.template > ../argus-device-manager.yaml

exit 0
