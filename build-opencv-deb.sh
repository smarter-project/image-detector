#!/usr/bin/env bash
set -e

# Config
MAINTAINER="Josh Minor"
VERSION=4.2.0

CURR_DIR=$(pwd)

sudo apt-get install build-essential cmake unzip pkg-config checkinstall
sudo apt-get install libjpeg-dev libpng-dev libtiff-dev
sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev
sudo apt-get install libv4l-dev libxvidcore-dev libx264-dev
sudo apt-get install libgtk-3-dev
sudo apt-get install libatlas-base-dev gfortran
sudo apt-get install python3-dev
			
# Make a new directory
find $CURR_DIR/opencv-build ! -name "*.zip" -exec rm -r {} \ || true
mkdir -p $CURR_DIR/opencv-build
cd $CURR_DIR/opencv-build

# Download OpenCV
FILE=opencv.zip
if [ -f "$FILE" ]; then
    echo "$FILE exists"
else
    echo "$FILE does not exist"
    wget -O opencv.zip https://github.com/opencv/opencv/archive/${VERSION}.zip
    unzip -q opencv.zip
fi

FILE=opencv_contrib.zip
if [ -f "$FILE" ]; then
    echo "$FILE exists"
else
    echo "$FILE does not exist"
    wget -O opencv_contrib.zip https://github.com/opencv/opencv_contrib/archive/${VERSION}.zip
    unzip -q opencv_contrib.zip
fi

cd opencv-${VERSION}
# Make build directory.
mkdir -p build
# Change to 
cd build

cmake -D CMAKE_BUILD_TYPE=RELEASE \
	-D CMAKE_INSTALL_PREFIX=/usr/local \
	-D INSTALL_PYTHON_EXAMPLES=OFF \
	-D INSTALL_C_EXAMPLES=OFF \
	-D OPENCV_ENABLE_NONFREE=ON \
	-D WITH_CUDA=ON \
	-D WITH_CUDNN=ON \
	-D OPENCV_DNN_CUDA=ON \
	-D ENABLE_FAST_MATH=1 \
	-D CUDA_FAST_MATH=1 \
	-D CUDA_ARCH_BIN=7.2 \
	-D WITH_CUBLAS=1 \
	-D OPENCV_EXTRA_MODULES_PATH=$CURR_DIR/opencv-build/opencv_contrib-${VERSION}/modules \
	-D HAVE_opencv_python3=ON \
	-D PYTHON_EXECUTABLE=/usr/bin/python3 \
	-D BUILD_EXAMPLES=OFF ..

make -j8

sudo checkinstall --default \
--type debian --install=no \
--pkgname opencv4 \
--pkgversion "${VERSION}" \
--pkglicense BSD \
--deldoc --deldesc --delspec \
--requires "libjpeg-dev,libpng-dev,libtiff-dev,libavcodec-dev,libavformat-dev,libswscale-dev,libv4l-dev,libxvidcore-dev,libx264-dev,libgtk-3-dev,libatlas-base-dev,gfortran" \
--pakdir ~ --maintainer "${MAINTAINER}" --provides opencv4 \
--addso --autodoinst \
make install
