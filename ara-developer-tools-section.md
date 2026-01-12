---

## Phase X: Developer Tools Setup

Install command-line tools for AI-assisted development and GitHub integration directly on the Pi.

---

### Step X.1: Generate SSH Key for GitHub

Set up SSH authentication for the `adarkazanli` GitHub account.

```bash
# Generate Ed25519 SSH key (more secure than RSA)
ssh-keygen -t ed25519 -C "adarkazanli@github" -f ~/.ssh/id_ed25519_github

# When prompted:
#   - Enter passphrase (recommended) or leave empty for no passphrase
```

**Start SSH agent and add key:**

```bash
# Start ssh-agent
eval "$(ssh-agent -s)"

# Add key to agent
ssh-add ~/.ssh/id_ed25519_github

# Make persistent across reboots - add to ~/.bashrc
echo 'eval "$(ssh-agent -s)" > /dev/null 2>&1' >> ~/.bashrc
echo 'ssh-add ~/.ssh/id_ed25519_github 2>/dev/null' >> ~/.bashrc
```

**Configure SSH for GitHub:**

```bash
# Create/edit SSH config
cat >> ~/.ssh/config << 'EOF'

# GitHub - adarkazanli
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github
    IdentitiesOnly yes
EOF

# Set proper permissions
chmod 600 ~/.ssh/config
chmod 600 ~/.ssh/id_ed25519_github
chmod 644 ~/.ssh/id_ed25519_github.pub
```

**Add public key to GitHub:**

```bash
# Display public key
cat ~/.ssh/id_ed25519_github.pub

# Copy the output, then:
# 1. Go to https://github.com/settings/keys
# 2. Click "New SSH key"
# 3. Title: "Ara Raspberry Pi"
# 4. Paste the key
# 5. Click "Add SSH key"
```

**Or use gh CLI to add the key (after gh is installed):**

```bash
gh ssh-key add ~/.ssh/id_ed25519_github.pub --title "Ara Raspberry Pi"
```

**Test SSH connection:**

```bash
ssh -T git@github.com

# Expected output:
# Hi adarkazanli! You've successfully authenticated...
```

---

### Step X.2: Install GitHub CLI (gh)

The official GitHub CLI for repository management, PRs, issues, and authentication.

> **Note:** If you added your SSH key via the web interface, you can use `gh auth login` and select SSH as the protocol.

```bash
# Add GitHub CLI repository
type -p curl >/dev/null || sudo apt install curl -y
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null

# Install gh
sudo apt update
sudo apt install gh -y

# Verify installation
gh --version
```

**Authenticate with GitHub:**

```bash
# Interactive login (recommended)
gh auth login

# Select:
#   - GitHub.com
#   - HTTPS
#   - Login with a web browser (or paste token)
```

**Quick verification:**

```bash
# Check auth status
gh auth status

# Test repo access
gh repo list --limit 5
```

---

### Step X.3: Install Node.js (Required for Claude Code)

Claude Code requires Node.js 18+.

```bash
# Install Node.js 20 LTS via NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
node --version   # Should be v20.x.x
npm --version
```

---

### Step X.4: Install Claude Code

Claude Code is Anthropic's AI-powered command-line coding assistant.

```bash
# Install globally via npm
sudo npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version
```

**Configure API key:**

```bash
# Option 1: Set environment variable (add to ~/.bashrc for persistence)
export ANTHROPIC_API_KEY="sk-ant-xxxxx"

# Option 2: Let Claude Code prompt on first run
claude

# Option 3: Store in config
echo 'export ANTHROPIC_API_KEY="sk-ant-xxxxx"' >> ~/.bashrc
source ~/.bashrc
```

**First run and authentication:**

```bash
cd ~/ara
claude

# Claude Code will:
# - Prompt for API key if not set
# - Initialize workspace context
# - Be ready for agentic coding tasks
```

**Useful Claude Code commands:**

```bash
# Start interactive session in project
cd ~/ara && claude

# Run with specific prompt
claude "explain the main.py file"

# Continue previous session
claude --continue
```

---

### Step X.5: Install GitHub Spec-Kit

Spec-kit enables spec-driven development workflows with GitHub integration.

```bash
cd ~/ara

# Clone spec-kit (or your fork)
git clone https://github.com/adarkazanli/spec-kit.git
cd spec-kit

# Install dependencies
npm install

# Link globally for CLI access
sudo npm link

# Verify
spec-kit --version
```

**Configure spec-kit for Ara project:**

```bash
cd ~/ara

# Initialize spec-kit in project
spec-kit init

# This creates:
#   - .spec-kit/ directory
#   - spec-kit.config.json
```

**Basic spec-kit workflow:**

```bash
# Create a new spec
spec-kit create "Add wake word detection"

# List specs
spec-kit list

# Generate implementation from spec
spec-kit generate <spec-id>

# Sync with GitHub issues
spec-kit sync
```

---

### Step X.6: Configure Git for Development

```bash
# Set identity (if not already configured)
git config --global user.name "Ammar Darkazanli"
git config --global user.email "your-email@example.com"

# Set default branch name
git config --global init.defaultBranch main

# Enable credential caching (1 hour)
git config --global credential.helper 'cache --timeout=3600'

# Useful aliases
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.cm "commit -m"
git config --global alias.lg "log --oneline --graph --decorate -10"
```

---

### Step X.7: Initialize Ara as Git Repository

```bash
cd ~/ara

# Initialize git repo
git init

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
venv/
__pycache__/
*.pyc
*.pyo
.pytest_cache/

# Models (large files - don't commit)
models/
*.gguf
*.bin

# Audio test files
*.wav
*.mp3

# Environment
.env
*.log

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
EOF

# Initial commit
git add .
git commit -m "Initial Ara voice assistant setup"

# Connect to GitHub (create repo first via gh)
gh repo create ara --private --source=. --remote=origin --push
```

---

### Developer Tools Quick Reference

| Tool | Command | Purpose |
|------|---------|---------|
| **gh** | `gh repo clone owner/repo` | Clone repository |
| **gh** | `gh pr create` | Create pull request |
| **gh** | `gh issue create` | Create issue |
| **gh** | `gh workflow run` | Trigger workflow |
| **claude** | `claude` | Start AI coding session |
| **claude** | `claude "do X"` | Run with prompt |
| **spec-kit** | `spec-kit create "title"` | Create new spec |
| **spec-kit** | `spec-kit sync` | Sync with GitHub |

---

### Troubleshooting

**gh auth issues:**
```bash
# Re-authenticate
gh auth logout
gh auth login

# Check token scopes
gh auth status
```

**Claude Code API errors:**
```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Check rate limits on Anthropic console
# https://console.anthropic.com/
```

**Node.js memory on Pi:**
```bash
# If npm install fails with memory errors, increase swap temporarily
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Run install again
npm install

# Restore swap after
sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=512/' /etc/dphys-swapfile
```

---

*Developer tools configured for Ara Voice Assistant — January 2026*

---

## Phase X+1: Backup — Clone microSD Card

After completing all setup, create a backup clone of your configured microSD card.

---

### Option A: Clone Using Another Linux/Mac Computer (Recommended)

This is the safest method — clone while the Pi is powered off.

**Step 1: Shut down the Pi cleanly**

```bash
# On the Pi
sudo shutdown -h now
```

**Step 2: Insert source SD card into your computer**

**Step 3: Identify the SD card device**

```bash
# On Linux
lsblk

# On Mac
diskutil list

# Look for your SD card (e.g., /dev/sdb or /dev/disk2)
# CAUTION: Double-check the device — wrong device = data loss!
```

**Step 4: Create the image backup**

```bash
# Linux - replace /dev/sdX with your device
sudo dd if=/dev/sdX of=~/ara-backup-$(date +%Y%m%d).img bs=4M status=progress

# Mac - replace diskN with your device, use rdisk for speed
sudo dd if=/dev/rdiskN of=~/ara-backup-$(date +%Y%m%d).img bs=4m status=progress
```

**Step 5: Shrink the image (optional but recommended)**

Full 64GB image is wasteful if you're only using 15GB. Use PiShrink:

```bash
# Install PiShrink
wget https://raw.githubusercontent.com/Drewsif/PiShrink/master/pishrink.sh
chmod +x pishrink.sh
sudo mv pishrink.sh /usr/local/bin/

# Shrink the image
sudo pishrink.sh ara-backup-20260112.img ara-backup-20260112-shrunk.img

# This typically reduces a 64GB image to ~5-8GB
```

**Step 6: Write to new SD card**

```bash
# Insert blank SD card, identify device again
lsblk  # or diskutil list on Mac

# Write image to new card
# Linux
sudo dd if=~/ara-backup-shrunk.img of=/dev/sdY bs=4M status=progress

# Mac
sudo dd if=~/ara-backup-shrunk.img of=/dev/rdiskN bs=4m status=progress

# Sync and eject
sync
```

---

### Option B: Clone Live on the Pi Using rpi-clone

Clone while the Pi is running — useful for quick backups.

**Step 1: Install rpi-clone**

```bash
cd ~
git clone https://github.com/billw2/rpi-clone.git
cd rpi-clone
sudo cp rpi-clone /usr/local/sbin/
sudo chmod +x /usr/local/sbin/rpi-clone
```

**Step 2: Insert destination SD card**

Use a USB SD card reader connected to the Pi.

```bash
# List devices to find the destination
lsblk

# Usually shows as /dev/sda when using USB reader
```

**Step 3: Clone to the new card**

```bash
# Clone to /dev/sda (adjust device as needed)
# -f = force, -U = generate new UUIDs
sudo rpi-clone sda -f -U

# Follow prompts:
#   - Confirm destination device
#   - Wait for clone (10-30 min depending on data size)
```

**Step 4: Verify the clone**

```bash
# Swap SD cards and boot from the clone
# Or mount and check files:
sudo mount /dev/sda2 /mnt
ls /mnt/home/pi/ara
sudo umount /mnt
```

---

### Option C: Quick Image Backup to External Drive

For periodic backups without a second SD card:

```bash
# Mount external USB drive
sudo mkdir -p /mnt/backup
sudo mount /dev/sda1 /mnt/backup

# Create compressed backup of SD card
sudo dd if=/dev/mmcblk0 bs=4M status=progress | gzip > /mnt/backup/ara-$(date +%Y%m%d).img.gz

# Unmount
sudo umount /mnt/backup
```

**Restore from compressed backup:**

```bash
gunzip -c ara-20260112.img.gz | sudo dd of=/dev/sdX bs=4M status=progress
```

---

### Backup Quick Reference

| Method | Pros | Cons |
|--------|------|------|
| **dd on computer** | Safest, offline backup | Requires card reader, second computer |
| **rpi-clone** | Live clone, easy | Needs USB card reader on Pi |
| **Compressed to USB** | Space efficient | Slower, full image size |

**Recommended backup schedule:**
- After initial setup: Full clone to spare SD card
- Weekly: Compressed backup to USB drive
- Before major changes: Quick rpi-clone

---

### Labeling Your SD Cards

Keep track of your cards:

```
┌─────────────────────────┐
│  ARA MAIN - 64GB        │
│  Created: 2026-01-12    │
│  Pi 4 8GB               │
└─────────────────────────┘

┌─────────────────────────┐
│  ARA BACKUP - 64GB      │
│  Cloned: 2026-01-12     │
│  From: ARA MAIN         │
└─────────────────────────┘
```

---

*Ara Voice Assistant — Fully configured and backed up — January 2026*
