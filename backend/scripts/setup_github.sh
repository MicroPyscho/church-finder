#!/usr/bin/env bash
set -euo pipefail

REPO_NAME="church-finder"
REPO_DESCRIPTION="Church property sale monitor — UK, within 2.5hrs of London"
REPO_VISIBILITY="private"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[setup]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }

info "Initialising git repository …"
git init
git add -A
git commit -m "feat: initial commit — church-finder full stack"

info "Creating branch structure …"
git checkout -b develop
git checkout -b staging
git checkout main 2>/dev/null || git checkout -b main

success "Branches: main, staging, develop"

info "Creating GitHub repository …"
gh repo create "$REPO_NAME" \
  --description "$REPO_DESCRIPTION" \
  --$REPO_VISIBILITY \
  --source=. \
  --remote=origin \
  --push

success "Repository created and main branch pushed"

git push origin staging develop
success "All branches pushed"

info "Configuring branch protection for 'main' …"
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/:owner/$REPO_NAME/branches/main/protection \
  --field required_status_checks='{"strict":true,"contexts":["Backend — lint + typecheck + unit tests","Frontend — typecheck + lint + build","Integration tests (Postgres)","Docker build + smoke test"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions=null \
  --field allow_force_pushes=false \
  --field allow_deletions=false

info "Configuring branch protection for 'staging' …"
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/:owner/$REPO_NAME/branches/staging/protection \
  --field required_status_checks='{"strict":true,"contexts":["Backend — lint + typecheck + unit tests","Frontend — typecheck + lint + build"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews=null \
  --field restrictions=null \
  --field allow_force_pushes=false

success "Branch protection rules set"

info "Creating GitHub Environments …"
gh api --method PUT -H "Accept: application/vnd.github+json" /repos/:owner/$REPO_NAME/environments/dev
gh api --method PUT -H "Accept: application/vnd.github+json" /repos/:owner/$REPO_NAME/environments/staging
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/:owner/$REPO_NAME/environments/production \
  --field wait_timer=0 \
  --field reviewers='[]' \
  --field deployment_branch_policy='{"protected_branches":true,"custom_branch_policies":false}'

success "Environments created: dev, staging, production"

echo ""
warn "═══════════════════════════════════════════════════════════"
warn "  ACTION REQUIRED: Add these secrets in GitHub Settings"
warn "  → Settings → Secrets and variables → Actions"
warn "═══════════════════════════════════════════════════════════"
echo ""
echo "  Repository secrets:"
echo "    NETLIFY_AUTH_TOKEN"
echo "    NETLIFY_SITE_ID"
echo ""
echo "  Staging environment secrets:"
echo "    STAGING_HOST, STAGING_USER, STAGING_SSH_KEY"
echo "    DB_PASSWORD, SMTP_USER, SMTP_PASSWORD, NOTIFY_EMAIL_TO"
echo ""
echo "  Production environment secrets:"
echo "    PROD_HOST, PROD_USER, PROD_SSH_KEY"
echo "    DB_PASSWORD, SECRET_KEY, SMTP_USER, SMTP_PASSWORD, NOTIFY_EMAIL_TO"
echo ""
success "Setup complete!"