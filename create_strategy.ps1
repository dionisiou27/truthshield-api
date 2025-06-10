Write-Host "TRUTHSHIELD STRATEGY SETUP" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Create folder structure
$folders = @(
    "STRATEGY",
    "STRATEGY\Meeting_Notes",
    "STRATEGY\Influencer_Research",
    "STRATEGY\Technical_Docs", 
    "STRATEGY\Pitch_Materials",
    "STRATEGY\Progress_Tracking",
    "STRATEGY\Private_HTML"
)

foreach ($folder in $folders) {
    New-Item -ItemType Directory -Force -Path $folder | Out-Null
    Write-Host "Created: $folder" -ForegroundColor Green
}

# Create empty MD files
$files = @(
    "STRATEGY\00_MASTER_PLAN.md",
    "STRATEGY\Quick_Links.md",    
    "STRATEGY\Influencer_Research\02_Target_List.md",
    "STRATEGY\Technical_Docs\03_Tech_Roadmap.md",
    "STRATEGY\Progress_Tracking\04_Progress.md"
)

foreach ($file in $files) {
    New-Item -ItemType File -Force -Path $file | Out-Null
    Write-Host "Created: $file" -ForegroundColor Yellow
}

Write-Host "" -ForegroundColor Green
Write-Host "SETUP COMPLETE!" -ForegroundColor Green
Write-Host "Open VS Code: code STRATEGY" -ForegroundColor Cyan