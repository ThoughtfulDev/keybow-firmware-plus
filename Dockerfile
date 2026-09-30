FROM debian:bookworm-slim AS build

# Debian armhf targets ARMv7; armel's static libraries also run on ARMv6.
# Extract only the target development packages to avoid multiarch version conflicts.
RUN dpkg --add-architecture armel \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        autoconf automake gcc-arm-linux-gnueabi \
        libc6-dev-armel-cross libtool make pkg-config \
    && mkdir /tmp/armel-debs \
    && cd /tmp/armel-debs \
    && apt-get download libconfig-dev:armel libpng-dev:armel zlib1g-dev:armel \
    && for deb in *.deb; do dpkg-deb -x "$deb" /; done \
    && rm -rf /tmp/armel-debs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY bcm2835-1.68/ bcm2835-1.68/
COPY libusbgx/ libusbgx/
COPY lua-5.4.0/ lua-5.4.0/
COPY keybow/ keybow/

ENV CC=arm-linux-gnueabi-gcc \
    CFLAGS="-O2 -marm -mcpu=arm1176jzf-s -mfpu=vfp -mfloat-abi=softfp" \
    PKG_CONFIG_LIBDIR=/usr/lib/arm-linux-gnueabi/pkgconfig:/usr/share/pkgconfig

RUN cd bcm2835-1.68 \
    && autoreconf -fi \
    && ./configure --host=arm-linux-gnueabi --prefix=/src/bcm2835-1.68/build \
    && make -j2 \
    && make install

RUN make -C lua-5.4.0 linux CC="$CC" MYCFLAGS="$CFLAGS"

RUN cd libusbgx \
    && autoreconf -fi \
    && ./configure --host=arm-linux-gnueabi --prefix=/src/libusbgx/build \
    && make -j2 \
    && make install

RUN make -C keybow

FROM scratch
COPY --from=build /src/keybow/keybow /keybow
