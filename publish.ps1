# PowerShell script to publish PaddleOCR-MCP to PyPI

Write-Host "Running tests..." -ForegroundColor Cyan
python -m pytest tests/ -v --tb=short

if ($LASTEXITCODE -ne 0) {
    Write-Host "Tests failed! Aborting publish." -ForegroundColor Red
    exit 1
}

Write-Host "`nAll tests passed! Building package..." -ForegroundColor Green
uv build

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Checking package..." -ForegroundColor Cyan
uvx twine check dist/*

if ($LASTEXITCODE -ne 0) {
    Write-Host "Package check failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`nPackage files:" -ForegroundColor Green
Get-ChildItem dist | Format-Table Name, Length -AutoSize

Write-Host "`nReady to publish! Choose an option:" -ForegroundColor Yellow
Write-Host "1. Test PyPI (recommended for first time)"
Write-Host "2. Production PyPI"
Write-Host "3. Cancel"

$choice = Read-Host "Enter choice (1-3)"

if ($choice -eq "1") {
    Write-Host "`nPublishing to Test PyPI..." -ForegroundColor Cyan
    Write-Host "Username: __token__" -ForegroundColor Yellow
    Write-Host "Password: (your testpypi API token)" -ForegroundColor Yellow
    uvx twine upload --repository testpypi dist/*
} elseif ($choice -eq "2") {
    Write-Host "`nPublishing to PyPI..." -ForegroundColor Cyan
    Write-Host "Username: __token__" -ForegroundColor Yellow
    Write-Host "Password: (your pypi API token)" -ForegroundColor Yellow
    uvx twine upload dist/*
} else {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit 0
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ Published successfully!" -ForegroundColor Green
    Write-Host "`nInstall with:" -ForegroundColor Cyan
    if ($choice -eq "1") {
        Write-Host "  pip install -i https://test.pypi.org/simple/ paddleocr-mcp" -ForegroundColor White
    } else {
        Write-Host "  pip install paddleocr-mcp" -ForegroundColor White
        Write-Host "  or: uvx paddleocr-mcp <image_path>" -ForegroundColor White
    }
} else {
    Write-Host "`n✗ Publish failed!" -ForegroundColor Red
    exit 1
}
