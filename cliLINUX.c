  build-macos-x64:
    name: macOS x86_64
    runs-on: macos-13

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install OpenSSL
        run: |
          brew install openssl@3

      - name: Build
        run: |
          mkdir -p bin

          clang \
            -O2 \
            ./cliLINUX.c \
            -o ./bin/cvp-macos-x64 \
            -I"$(brew --prefix openssl@3)/include" \
            -L"$(brew --prefix openssl@3)/lib" \
            -lcrypto

      - name: Check
        run: |
          file ./bin/cvp-macos-x64
          ./bin/cvp-macos-x64 --version

      - name: Upload
        uses: actions/upload-artifact@v4
        with:
          name: cvp-macos-x64
          path: bin/cvp-macos-x64
