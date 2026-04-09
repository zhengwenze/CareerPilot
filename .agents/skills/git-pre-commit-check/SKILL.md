---
name: git-pre-commit-check
description: Use this skill to perform pre-commit checks including sensitive data scanning, large file detection, code quality validation, and test reminders before creating Git commits.
---

# Git Pre-commit Check

Use this skill when the user wants to:

- 检查提交前的代码质量
- 扫描敏感信息
- 检查大文件
- 验证代码规范
- 提醒运行测试
- pre-commit checks
- validate before commit

## Goals

- prevent accidental commit of sensitive data
- avoid committing oversized files
- ensure code quality standards
- remind about testing before committing
- catch common issues early in the workflow

## Prerequisites Checklist

Before running pre-commit checks:

- [ ] Git repository initialized
- [ ] Files staged or working tree has changes
- [ ] Required tools available (grep, awk, etc.)

## Default execution path

When this skill is triggered:

1. Check if there are changes to commit
2. Run sensitive data scan
3. Check for large files
4. Validate code quality (if applicable)
5. Remind about tests
6. Report findings and recommendations

## Check Categories

### 1. Sensitive Data Scan

Scan for common sensitive patterns:

#### API Keys and Tokens
```bash
# Scan for common API key patterns
git diff --cached --name-only | xargs grep -l -E \
  '(api[_-]?key|apikey|api[_-]?secret|auth[_-]?token|access[_-]?token|private[_-]?key|secret[_-]?key)\s*[=:]\s*["\047][a-zA-Z0-9]{16,}["\047]' \
  2>/dev/null || echo "No obvious API keys found"
```

#### Password Patterns
```bash
# Check for password patterns
git diff --cached --name-only | xargs grep -l -i -E \
  '(password|passwd|pwd)\s*[=:]\s*["\047][^"\047]{4,}["\047]' \
  2>/dev/null || echo "No obvious passwords found"
```

#### Private Keys
```bash
# Check for private key files
git diff --cached --name-only | xargs grep -l \
  'BEGIN \(RSA\|DSA\|EC\|OPENSSH\|PGP\) PRIVATE KEY' \
  2>/dev/null || echo "No private keys found"
```

#### Environment Files
```bash
# Check if .env files are being committed
git diff --cached --name-only | grep -E '\.env($|\.)' || echo "No .env files in commit"
```

**Action on detection**:
- STOP the commit process
- List the files containing sensitive data
- Suggest adding to `.gitignore`
- Recommend using environment variables or secret management

### 2. Large File Detection

Check for files that should use Git LFS:

```bash
# Check for files > 10MB in staged changes
git diff --cached --numstat | awk '$1 > 10485760 || $2 > 10485760 {
    print "WARNING: Large file detected: " $3
    print "  Size: " ($1+$2) " bytes"
    print "  Consider using Git LFS or adding to .gitignore"
}'
```

**Common large file types to check**:
- Images: `.png`, `.jpg`, `.gif`, `.svg` (if large)
- Videos: `.mp4`, `.mov`, `.avi`
- Archives: `.zip`, `.tar.gz`, `.rar`
- Binaries: `.exe`, `.dll`, `.so`
- Data files: `.csv`, `.json` (if large)

**Action on detection**:
- WARN about large files
- Suggest Git LFS setup
- Provide `.gitignore` template

### 3. Code Quality Validation

#### Trailing Whitespace
```bash
# Check for trailing whitespace
git diff --cached --check 2>/dev/null || echo "Trailing whitespace issues found"
```

#### Merge Conflict Markers
```bash
# Check for unresolved merge conflicts
git diff --cached --name-only | xargs grep -l '<<<<<<< HEAD' 2>/dev/null && \
  echo "ERROR: Merge conflict markers found" || echo "No conflict markers"
```

#### Syntax Validation (Language-specific)

For Python:
```bash
# Check Python syntax
find . -name "*.py" -type f -exec python -m py_compile {} \; 2>&1 | head -20
```

For JavaScript/TypeScript:
```bash
# Check if eslint is available and run it
if command -v eslint &> /dev/null; then
  git diff --cached --name-only --diff-filter=ACM | grep -E '\.(js|jsx|ts|tsx)$' | xargs eslint 2>/dev/null
fi
```

### 4. Test Reminders

Check if tests exist and remind to run them:

```bash
# Check for test files
test_files=$(find . -name "*test*" -o -name "*spec*" | grep -E '\.(py|js|ts|java|go)$' | head -5)
if [ -n "$test_files" ]; then
  echo "📋 Test files found:"
  echo "$test_files"
  echo "💡 Remember to run tests before committing!"
fi
```

**Common test commands to suggest**:
- Python: `pytest`, `python -m unittest`
- JavaScript: `npm test`, `yarn test`
- Java: `mvn test`, `gradle test`
- Go: `go test ./...`

### 5. File Permission Checks

Check for executable files that shouldn't be:

```bash
# List executable non-script files
git diff --cached --name-only --diff-filter=ACM | while read file; do
  if [ -x "$file" ] && [[ ! "$file" =~ \.(sh|py|js|rb|pl)$ ]]; then
    echo "WARNING: Executable file (may not need +x): $file"
  fi
done
```

## Integration with dual-repo-publish

The `dual-repo-publish` skill should call this skill before staging files:

```
dual-repo-publish workflow:
1. git status --short
2. **Run git-pre-commit-check** (this skill)
3. If checks pass → continue with commit
4. If issues found → report and stop (or continue with user confirmation)
5. Stage files
6. Generate commit message
7. Create commit
8. Push to remotes
```

## Output Format

### Success Output
```
✅ Pre-commit checks passed

Summary:
- Sensitive data: No issues found
- Large files: No issues found
- Code quality: No issues found
- Test reminder: 5 test files found

Ready to commit!
```

### Warning Output
```
⚠️  Pre-commit checks completed with warnings

Warnings:
1. Large file detected: assets/video.mp4 (25MB)
   → Consider using Git LFS

2. Test files modified but tests not run
   → Remember to run: pytest

Continue with commit? (y/n)
```

### Error Output
```
❌ Pre-commit checks failed

Errors:
1. Sensitive data detected in config.py:
   Line 15: API_KEY = "sk-abc123..."
   → Move to environment variables

2. Merge conflict markers in main.py
   → Resolve conflicts before committing

Commit blocked. Please fix issues above.
```

## Quick Reference

| Check | Command | Severity |
|-------|---------|----------|
| API keys | `git diff --cached | grep -i api_key` | ERROR |
| Private keys | `git diff --cached | grep "PRIVATE KEY"` | ERROR |
| .env files | `git diff --cached --name-only | grep \\.env` | ERROR |
| Large files (>10MB) | `git diff --cached --numstat` | WARNING |
| Trailing whitespace | `git diff --cached --check` | WARNING |
| Merge conflicts | `grep -r "<<<<<<<" .` | ERROR |
| Test reminder | `find . -name "*test*.py"` | INFO |

## Common Issues and Solutions

### Issue: Accidentally committed sensitive data

**Solution**:
1. Do not push to remote
2. Use `git reset HEAD~1` to undo last commit
3. Add to `.gitignore`
4. Commit again without sensitive files

### Issue: Large file already committed

**Solution**:
1. Use Git LFS: `git lfs track "*.psd"`
2. Or remove from history: `git filter-branch` or BFG Repo-Cleaner
3. Force push (coordinate with team)

### Issue: Merge conflicts committed

**Solution**:
1. Undo commit: `git reset HEAD~1`
2. Resolve conflicts
3. Re-commit

## Best Practices

1. **Always run checks before committing**
2. **Fix errors immediately** - don't postpone
3. **Review warnings carefully** - some may be acceptable
4. **Add custom checks** for project-specific requirements
5. **Keep `.gitignore` updated** to prevent accidental commits
6. **Use Git LFS** for binary files from the start
7. **Never commit `.env` files** - use templates instead (`.env.example`)

## Example .gitignore Template

```gitignore
# Environment files
.env
.env.local
.env.*.local

# Secrets
*.pem
*.key
secrets/
config/secrets.yml

# Large files
*.mp4
*.mov
*.avi
*.zip
*.tar.gz
*.psd
*.sketch

# Dependencies
node_modules/
vendor/
__pycache__/

# Build outputs
dist/
build/
*.min.js
*.min.css
```
