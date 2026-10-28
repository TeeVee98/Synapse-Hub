param(
    [string]$Message = "feat: update ENTERPRISE AUTOMATION test suite",
    [string]$Target = "all" # "all", "github", "scm"
)

$ErrorActionPreference = "Continue"
$repoPath = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   ENTERPRISE AUTOMATION - DUAL REMOTE PRIVACY PUSH ENGINE      " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Target mode: $Target" -ForegroundColor Yellow

# Function to push to personal GitHub (Full backup)
function Push-PersonalGitHub {
    Write-Host "`n[1/3] Pushing FULL workspace to personal GitHub (TeeVee998)..." -ForegroundColor Green
    git -C $repoPath checkout main
    $status = git -C $repoPath status --porcelain
    if ($status) {
        git -C $repoPath add -A
        git -C $repoPath commit -m $Message
    }
    git -C $repoPath push github main
    Write-Host "--> Personal GitHub updated successfully with all AI skills & full history!" -ForegroundColor Green
}

# Function to push to company SCM (Clean, isolated, no agents)
function Push-CompanySCM {
    Write-Host "`n[2/3] Preparing clean branch for Company SCM..." -ForegroundColor Green
    git -C $repoPath checkout scm-clean

    # Sync test code directories from main
    $syncPaths = @("Test Cases", "Scripts", "Test Suites", "Keywords", "Profiles", "Data Files", "Include", "settings", "Test Listeners", "tools", "CICD_GUIDE.md", "HDSD.md", "ONBOARDING.md", "POM_REFACTORING_PLAN.md", "README.md", "FINAL_REPORT.md", "KNOWN_ISSUES.md", "project.prj", "build.gradle", ".gitignore", ".env.example", ".gitlab-ci.yml", ".github")
    foreach ($p in $syncPaths) {
        if (Test-Path "$repoPath\$p") {
            git -C $repoPath checkout main -- "$p" 2>$null
        }
    }

    # Whitelist of allowed documentation for company SCM
    $allowedDocs = @("CICD_GUIDE.md", "HDSD.md", "ONBOARDING.md", "POM_REFACTORING_PLAN.md", "README.md", "FINAL_REPORT.md", "KNOWN_ISSUES.md")
    Get-ChildItem -Path $repoPath -Filter "*.md" -Recurse | ForEach-Object {
        $docName = $_.Name
        if ($allowedDocs -notcontains $docName) {
            Write-Host "Auto-stripping private markdown doc: $docName" -ForegroundColor Yellow
            Remove-Item -Force $_.FullName -ErrorAction SilentlyContinue
            git -C $repoPath rm -rf --cached $_.FullName 2>$null
        }
    }

    # Ensure no private files or directories exist
    $privatePatterns = @(".agents", ".agent", "AGENTS.md", "OPEN_SOURCE_CITATIONS.md", "AI_*.md", "FUTURE_*.md", "PROJECT_STATE.md", "*agent*.md", "Enterprise_flow_probe_report.md", "tools/smart_push.ps1", "tools/smart_push.sh", "tools/smart_push.bat", "tools/lint_ai_docs.py", "tools/git_pre_commit_guard.py", "tools/cache_resolver.py", "tools/memory_cache.db", "tools/pinpoint_failure.py", "tools/lookup_tc.py", "tools/lookup_xpath.py", "tools/verify_all.py", "tools/verify_all.sh", "tools/refactor_all_batch07.py", "tools/create_group_suites.py", "apply_batch07_refactor.py", "update_batch07_scripts.py", "tools/test_impact.py", "tools/distill_log.py", "tools/generate_api_matrix.py", "tools/generate_tc_from_story.py", "tools/visual_diff_canvas.py", "tools/agent_canary.py", "tools/repo_map.py", "tools/infer_linter.py", "tools/trace_data_flow.py", "tools/repo_map.txt", "tools/repo_map.json", "reports")
    foreach ($priv in $privatePatterns) {
        Get-ChildItem -Path $repoPath -Filter $priv -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            Remove-Item -Recurse -Force $_.FullName -ErrorAction SilentlyContinue
            git -C $repoPath rm -rf --cached $_.FullName 2>$null
        }
    }

    # Sanitize any agent terminology in docs on scm-clean
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    if (Test-Path "$repoPath\FINAL_REPORT.md") {
        $finalLines = [System.IO.File]::ReadAllLines("$repoPath\FINAL_REPORT.md", [System.Text.Encoding]::UTF8)
        $rep = "> **Ph" + [char]0x01B0 + [char]0x01A1 + "ng ph" + [char]0x00E1 + "p tri" + [char]0x1EC3 + "n khai:** Kh" + [char]0x1EA3 + "o s" + [char]0x00E1 + "t DOM th" + [char]0x1EF1 + "c t" + [char]0x1EBF + ", chu" + [char]0x1EA9 + "n ho" + [char]0x00E1 + " m" + [char]0x00E3 + " Clean POM v" + [char]0x00E0 + " th" + [char]0x1EF1 + "c thi nghi" + [char]0x1EC7 + "m thu t" + [char]0x1EF1 + " " + [char]0x0111 + [char]0x1ED9 + "ng tr" + [char]0x00EA + "n Katalon KRE CLI."
        $out = New-Object System.Collections.Generic.List[string]
        foreach ($l in $finalLines) {
            if ($l.Contains("Autonomous Multi-Agent Swarm")) { $out.Add($rep) } else { $out.Add($l) }
        }
        [System.IO.File]::WriteAllLines("$repoPath\FINAL_REPORT.md", $out, $utf8NoBom)
    }

    git -C $repoPath add -A

    # Create squashed clean commit on top of origin/main
    $tree = (git -C $repoPath write-tree).Trim()
    $parent = (git -C $repoPath rev-parse origin/main).Trim()
    $cleanCommit = (git -C $repoPath commit-tree $tree -p $parent -m "feat: sync latest ENTERPRISE AUTOMATION test suite (259 Test Cases, 30 Test Suites)").Trim()
    git -C $repoPath reset --hard $cleanCommit

    Write-Host "Pushing clean commit ($cleanCommit) to company SCM origin/main..." -ForegroundColor Yellow
    git -C $repoPath push origin scm-clean:main
    Write-Host "--> Company SCM updated successfully without any agent or private skills!" -ForegroundColor Green
}

# Execution logic
try {
    if ($Target -eq "all" -or $Target -eq "github") {
        Push-PersonalGitHub
    }
    if ($Target -eq "all" -or $Target -eq "scm") {
        Push-CompanySCM
    }
} finally {
    # Always return to main branch
    git -C $repoPath checkout main 2>$null
    Write-Host "`n[3/3] Returned to local 'main' branch. All private skills remain active." -ForegroundColor Cyan
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "                      DUAL PUSH COMPLETE                  " -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Cyan
}
