# Crypto Crew - User Command Guide

## 🚀 Execution Commands
- `cryptoactivestart`: **High Performance Mode**. Uses 7 Cores, 12GB RAM, and GPU. Recommended for active optimization.
- `cryptopassivestart`: **Background Mode**. Uses 1 Core (2 threads), 6GB RAM. Best for low-impact long-term runs.
- `cryptostop`: **Smooth Stop**. Sends a termination signal; the bot will finish the current generation before exiting.
- `cryptohardstop`: **Emergency Stop**. Instantly kills all agent and bot processes.

## 📊 Monitoring
- **Live AI Thinking**: `tail -f ~/crypto_crew/ai_thinking.live` (Real-time reasoning, ideas, and data inputs).
- **Generational Reflections**: `tail -f ~/crypto_crew/ai_reflection.log` (Summary of results and robustness scores).
- **Agent Logs**: `tail -f ~/crypto_crew/agent_crew.log` (Raw technical output).

## 📦 Maintenance & Portability
- **Export Setup**: Run `~/crypto_crew/export_setup.sh` to generate `crypto_crew_export.tar.gz`.
- **Install on New PC**: Transfer the tarball, run `tar -xzf crypto_crew_export.tar.gz && ./install_crew.sh`.

---
*Note: All management files and evolved strategies are located in `~/crypto_crew/`.*
