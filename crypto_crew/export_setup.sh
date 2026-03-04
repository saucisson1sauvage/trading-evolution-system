#!/bin/bash
# Comprehensive Export Script - Auto-updates the "Brain" package

EXPORT_FILE="/home/saus/crypto_crew/crypto_crew_export.tar.gz"
TEMP_DIR="/home/saus/crypto_crew/crew_export_tmp"

# Create clean structure
mkdir -p $TEMP_DIR/strategies
mkdir -p $TEMP_DIR/logs

# 1. Copy Management Scripts
cp /home/saus/crypto_crew/autonomous_agent.py $TEMP_DIR/
cp /home/saus/crypto_crew/monitor_mem.sh $TEMP_DIR/
cp /home/saus/crypto_crew/hard_stop.sh $TEMP_DIR/
cp /home/saus/crypto_crew/smooth_stop.sh $TEMP_DIR/
cp /home/saus/crypto_crew/start_high_res.sh $TEMP_DIR/
cp /home/saus/crypto_crew/start_low_res.sh $TEMP_DIR/
cp /home/saus/crypto_crew/export_setup.sh $TEMP_DIR/

# 2. Copy Configuration & Global Logs
# FIX: freqtrade is in /home/saus/freqtrade, NOT /home/saus/crypto_crew/freqtrade
cp /home/saus/freqtrade/user_data/config.json $TEMP_DIR/
[ -f /home/saus/crypto_crew/agent_history.log ] && cp /home/saus/crypto_crew/agent_history.log $TEMP_DIR/logs/

# 3. Copy Strategy Files (Python + Evolved JSON Parameters)
cp /home/saus/freqtrade/user_data/strategies/EvolutionaryVolScaler.py $TEMP_DIR/strategies/
[ -f /home/saus/freqtrade/user_data/strategies/EvolutionaryVolScaler.json ] && cp /home/saus/freqtrade/user_data/strategies/EvolutionaryVolScaler.json $TEMP_DIR/strategies/

# 4. Create Improved Installer
cat << 'EOF' > $TEMP_DIR/install_crew.sh
#!/bin/bash
echo "Installing/Updating Crypto Crew on this machine..."

# Recreate folders
mkdir -p ~/freqtrade/user_data/strategies
mkdir -p ~/freqtrade/user_data/backtest_results
mkdir -p ~/freqtrade/user_data/hyperopt_results

# Move core files to home
mkdir -p ~/crypto_crew
cp autonomous_agent.py monitor_mem.sh *.sh ~/crypto_crew/
chmod +x ~/crypto_crew/*.sh

# Move strategy and config
cp config.json ~/freqtrade/user_data/
cp strategies/* ~/freqtrade/user_data/strategies/
[ -d logs ] && cp logs/* ~/crypto_crew/

echo "Installation complete. Aliases remain in your bashrc/fish if previously installed."
EOF

chmod +x $TEMP_DIR/install_crew.sh

# Compress and overwrite the old package
tar -czf $EXPORT_FILE -C $TEMP_DIR .

# Cleanup
rm -rf $TEMP_DIR
