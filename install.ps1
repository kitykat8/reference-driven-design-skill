#Requires -Version 5.1
$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "  Installing Reference-Driven Design Skill (Antigravity/AI) " -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow

# 1. Install Python dependencies
Write-Host "`n[1/3] Installing Python dependencies (Pillow, PyMuPDF, python-pptx)..." -ForegroundColor Cyan
python -m pip install -r "$PSScriptRoot\requirements.txt"

# 2. Copy skill to global Antigravity / Gemini skills directory
$TargetSkillsDir = Join-Path $HOME ".gemini\config\skills\reference-driven-design"
Write-Host "`n[2/3] Copying skill files to: $TargetSkillsDir" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $TargetSkillsDir | Out-Null
Copy-Item -Path "$PSScriptRoot\skills\reference-driven-design\*" -Destination $TargetSkillsDir -Recurse -Force

# Replace username placeholder in SKILL.md if needed
$SkillMdPath = Join-Path $TargetSkillsDir "SKILL.md"
if (Test-Path $SkillMdPath) {
    $Content = Get-Content $SkillMdPath -Raw -Encoding UTF8
    $Content = $Content.Replace("C:\Users\rusla\.gemini\config\skills\reference-driven-design", $TargetSkillsDir)
    Set-Content -Path $SkillMdPath -Value $Content -Encoding UTF8
}

# 3. Verify installation
Write-Host "`n[3/3] Verifying scripts..." -ForegroundColor Cyan
python "$TargetSkillsDir\scripts\fetch_references.py" --help | Out-Null
python "$TargetSkillsDir\scripts\cutout_assets.py" --help | Out-Null
python "$TargetSkillsDir\scripts\export_presentation.py" --help | Out-Null

Write-Host "`n[OK] Reference-Driven Design skill successfully installed!" -ForegroundColor Green
Write-Host "Location: $TargetSkillsDir" -ForegroundColor Gray
