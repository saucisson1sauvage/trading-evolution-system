#!/bin/bash
# DeepSeek V3 API Key
export DEEPSEEK_API_KEY="sk-ebbc7d4c678b493eb3ca38a6f3fa30e0"

# Run Aider with DeepSeek-V3
# Using --attribute-author/committer to keep your git history clean if you use git
/home/saus/aider_venv/bin/aider --model deepseek/deepseek-chat "$@"
