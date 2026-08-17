name: Build on macOS

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build-macos:
    runs-on: macos-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          brew update
          brew install ninja cmake

      - name: Configure project
        run: cmake -B build -G Ninja

      - name: Build project
        run: cmake --build build --config Release

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: macos-build
          path: build/**
