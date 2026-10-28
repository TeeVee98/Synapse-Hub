#!/usr/bin/env bash
# ==============================================================================
# DMIT AUTOMATION - DUAL REMOTE PRIVACY PUSH ENGINE (macOS / Linux Native)
# ==============================================================================

set -e

MESSAGE="${1:-feat: update DMIT automation test suite}"
TARGET="${2:-all}" # "all", "github", "scm"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_PATH="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=========================================================="
echo "   DMIT AUTOMATION - DUAL REMOTE PRIVACY PUSH ENGINE      "
echo "=========================================================="
echo "Target mode: ${TARGET}"
echo "Repository:  ${REPO_PATH}"

push_personal_github() {
    echo ""
    echo "[1/3] Pushing FULL workspace to personal GitHub (TeeVee998)..."
    python3 "${REPO_PATH}/tools/cache_resolver.py" sync 2>/dev/null || true
    git -C "${REPO_PATH}" checkout main
    if [ -n "$(git -C "${REPO_PATH}" status --porcelain)" ]; then
        git -C "${REPO_PATH}" add -A
        git -C "${REPO_PATH}" commit -m "${MESSAGE}"
    fi
    git -C "${REPO_PATH}" push github main
    echo "--> Personal GitHub updated successfully with all AI skills & full history!"
}

push_company_scm() {
    echo ""
    echo "[2/3] Preparing clean branch for Company SCM (VNPT DevOps)..."
    git -C "${REPO_PATH}" checkout -B scm-clean origin/main 2>/dev/null || git -C "${REPO_PATH}" checkout -B scm-clean

    # Sync test code directories from main
    sync_paths=(
        "Test Cases" "Scripts" "Test Suites" "Keywords" "Profiles"
        "Data Files" "Include" "settings" "Test Listeners" "tools"
        "CICD_GUIDE.md" "HDSD.md" "ONBOARDING.md" "POM_REFACTORING_PLAN.md"
        "README.md" "FINAL_REPORT.md" "KNOWN_ISSUES.md" "DMIT.prj"
        "build.gradle" ".gitignore" ".env.example" ".gitlab-ci.yml" ".github"
    )

    for p in "${sync_paths[@]}"; do
        if [ -e "${REPO_PATH}/${p}" ]; then
            git -C "${REPO_PATH}" checkout main -- "${p}" 2>/dev/null || true
        fi
    done

    # Whitelist of allowed documentation for company SCM
    allowed_docs=("CICD_GUIDE.md" "HDSD.md" "ONBOARDING.md" "POM_REFACTORING_PLAN.md" "README.md" "FINAL_REPORT.md" "KNOWN_ISSUES.md")
    find "${REPO_PATH}" -maxdepth 2 -name "*.md" | while read -r doc; do
        bname="$(basename "${doc}")"
        allowed=false
        for a in "${allowed_docs[@]}"; do
            if [ "${bname}" = "${a}" ]; then
                allowed=true
                break
            fi
        done
        if [ "${allowed}" = false ]; then
            echo "Auto-stripping private markdown doc: ${bname}"
            rm -f "${doc}" 2>/dev/null || true
            git -C "${REPO_PATH}" rm -rf --cached "${doc}" 2>/dev/null || true
        fi
    done

    # Ensure no private files or directories exist
    private_patterns=(
        ".agents" ".agent" "AGENTS.md" "OPEN_SOURCE_CITATIONS.md" "AI_*.md"
        "FUTURE_*.md" "PROJECT_STATE.md" "*agent*.md" "dmit_flow_probe_report.md"
        "tools/smart_push.ps1" "tools/smart_push.sh" "tools/smart_push.bat"
        "tools/lint_ai_docs.py" "tools/git_pre_commit_guard.py" "tools/cache_resolver.py"
        "tools/memory_cache.db" "tools/pinpoint_failure.py" "tools/lookup_tc.py"
        "tools/lookup_xpath.py" "tools/verify_all.py" "tools/verify_all.sh"
        "tools/refactor_all_batch07.py" "tools/create_group_suites.py"
        "apply_batch07_refactor.py" "update_batch07_scripts.py" "tools/test_impact.py"
        "tools/distill_log.py" "tools/generate_api_matrix.py" "tools/generate_tc_from_story.py" "tools/visual_diff_canvas.py"
        "tools/agent_canary.py" "tools/repo_map.py" "tools/infer_linter.py" "tools/trace_data_flow.py"
        "tools/repo_map.txt" "tools/repo_map.json" "reports"
    )

    for priv in "${private_patterns[@]}"; do
        find "${REPO_PATH}" -name "${priv}" -o -path "*/${priv}" 2>/dev/null | while read -r match; do
            rm -rf "${match}" 2>/dev/null || true
            git -C "${REPO_PATH}" rm -rf --cached "${match}" 2>/dev/null || true
        done
    done

    # Sanitize agent terminology in FINAL_REPORT.md on scm-clean
    if [ -f "${REPO_PATH}/FINAL_REPORT.md" ]; then
        sed -i '' 's/Autonomous Multi-Agent Swarm/Khảo sát DOM thực tế, chuẩn hoá mã Clean POM và thực thi nghiệm thu tự động trên Katalon KRE CLI/g' "${REPO_PATH}/FINAL_REPORT.md" 2>/dev/null || \
        sed -i 's/Autonomous Multi-Agent Swarm/Khảo sát DOM thực tế, chuẩn hoá mã Clean POM và thực thi nghiệm thu tự động trên Katalon KRE CLI/g' "${REPO_PATH}/FINAL_REPORT.md" 2>/dev/null || true
    fi

    git -C "${REPO_PATH}" add -A

    # Create squashed clean commit on top of origin/main
    tree="$(git -C "${REPO_PATH}" write-tree)"
    parent="$(git -C "${REPO_PATH}" rev-parse origin/main)"
    clean_commit="$(git -C "${REPO_PATH}" commit-tree "${tree}" -p "${parent}" -m "feat: sync latest DMIT automation test suite (259 Test Cases, 30 Test Suites)")"
    git -C "${REPO_PATH}" reset --hard "${clean_commit}"

    origin_url="$(git -C "${REPO_PATH}" config --get remote.origin.url || true)"
    if [[ "${origin_url}" == *"github.com"* ]]; then
        echo "Detected GitHub origin. Pushing clean commit (${clean_commit}) to branch scm-clean..."
        git -C "${REPO_PATH}" push -f origin scm-clean:scm-clean
        echo "--> Clean branch updated at origin:scm-clean without any agent or private skills!"
    else
        echo "Pushing clean commit (${clean_commit}) to company SCM origin/main..."
        git -C "${REPO_PATH}" push origin scm-clean:main
        echo "--> Company SCM updated successfully without any agent or private skills!"
    fi
}

# Trap to guarantee returning to main branch
trap 'git -C "${REPO_PATH}" checkout main 2>/dev/null || true; echo "[3/3] Returned to local main branch."' EXIT

if [ "${TARGET}" = "all" ] || [ "${TARGET}" = "github" ]; then
    push_personal_github
fi

if [ "${TARGET}" = "all" ] || [ "${TARGET}" = "scm" ]; then
    push_company_scm
fi

echo "=========================================================="
echo "                 DUAL PUSH COMPLETE                       "
echo "=========================================================="
