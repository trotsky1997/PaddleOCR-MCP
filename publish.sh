#!/bin/bash
# Bash script to publish PaddleOCR-MCP to PyPI

echo "Building package..."
uv build

if [ $? -ne 0 ]; then
    echo "Build failed!"
    exit 1
fi

echo "Checking package..."
uvx twine check dist/*

if [ $? -ne 0 ]; then
    echo "Package check failed!"
    exit 1
fi

echo -e "\nPackage files:"
ls -lh dist/

echo -e "\nReady to publish! Choose an option:"
echo "1. Test PyPI (recommended for first time)"
echo "2. Production PyPI"
echo "3. Cancel"

read -p "Enter choice (1-3): " choice

if [ "$choice" == "1" ]; then
    echo -e "\nPublishing to Test PyPI..."
    echo "Username: __token__"
    echo "Password: (your testpypi API token)"
    uvx twine upload --repository testpypi dist/*
elif [ "$choice" == "2" ]; then
    echo -e "\nPublishing to PyPI..."
    echo "Username: __token__"
    echo "Password: (your pypi API token)"
    uvx twine upload dist/*
else
    echo "Cancelled."
    exit 0
fi

if [ $? -eq 0 ]; then
    echo -e "\n✓ Published successfully!"
    echo -e "\nInstall with:"
    if [ "$choice" == "1" ]; then
        echo "  pip install -i https://test.pypi.org/simple/ paddleocr-mcp"
    else
        echo "  pip install paddleocr-mcp"
        echo "  or: uvx paddleocr-mcp <image_path>"
    fi
else
    echo -e "\n✗ Publish failed!"
    exit 1
fi
