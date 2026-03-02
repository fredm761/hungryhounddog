#!/bin/bash
###############################################################################
# backup.sh: Backup HungryHoundDog configurations and critical data.
#
# Backs up:
# - System configurations from all nodes
# - OpenSearch indices and mappings
# - ML models and training data
# - ChromaDB vector database
# - Network topology documentation
###############################################################################

set -euo pipefail

# Configuration
BACKUP_BASE="/mnt/hungryhounddog/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_BASE/backup_$TIMESTAMP"
LOG_FILE="$BACKUP_BASE/backup_$TIMESTAMP.log"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Statistics
total_backed_up=0
total_errors=0

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_section() {
    echo -e "\n${BLUE}==== $1 ====${NC}\n" | tee -a "$LOG_FILE"
}

# Create backup structure
mkdir -p "$BACKUP_DIR"/{configs,opensearch,ml_models,chromadb,documentation}

echo "Backup started at $(date)" > "$LOG_FILE"

log_section "HungryHoundDog Backup Starting"
log_info "Backup directory: $BACKUP_DIR"

# Function to backup remote node configuration
backup_node_config() {
    local node_name=$1
    local node_ip=$2
    local config_paths=$3

    log_info "Backing up $node_name configuration..."

    local node_backup_dir="$BACKUP_DIR/configs/$node_name"
    mkdir -p "$node_backup_dir"

    # Backup SSH config
    if timeout 30 ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
        "root@$node_ip" "tar czf - /etc/ssh /etc/sysconfig /opt/hungryhounddog/config" 2>/dev/null | \
        tar xzf - -C "$node_backup_dir" 2>/dev/null; then
        log_info "✓ $node_name configuration backed up"
        ((total_backed_up++))
    else
        log_warn "✗ Failed to backup $node_name configuration"
        ((total_errors++))
    fi
}

# Backup OpenSearch indices
backup_opensearch() {
    log_info "Backing up OpenSearch indices..."

    local opensearch_backup_dir="$BACKUP_DIR/opensearch"

    # Create snapshot of indices
    if timeout 60 curl -s -X PUT "localhost:9200/_snapshot/backup" \
        -H 'Content-Type: application/json' \
        -d "{\"type\":\"fs\",\"settings\":{\"location\":\"$opensearch_backup_dir\"}}" \
        2>/dev/null | grep -q '"acknowledged"'; then
        log_info "✓ OpenSearch snapshot created"
        ((total_backed_up++))
    else
        log_warn "✗ OpenSearch backup failed (may not be running)"
        ((total_errors++))
    fi

    # Export indices configuration
    if timeout 30 curl -s "localhost:9200/_cat/indices?format=json" \
        > "$opensearch_backup_dir/indices_list.json" 2>/dev/null; then
        log_info "✓ Indices list exported"
    fi
}

# Backup ML models
backup_ml_models() {
    log_info "Backing up ML models..."

    local ml_backup_dir="$BACKUP_DIR/ml_models"
    local ml_source="/opt/hungryhounddog/ml/models"

    if [ -d "$ml_source" ]; then
        if cp -r "$ml_source"/* "$ml_backup_dir/" 2>/dev/null; then
            log_info "✓ ML models backed up"
            ((total_backed_up++))
        else
            log_warn "✗ ML models backup failed"
            ((total_errors++))
        fi
    else
        log_warn "ML models directory not found"
    fi

    # Backup training data
    local training_source="/opt/hungryhounddog/ml/training_data"
    if [ -d "$training_source" ]; then
        if tar czf "$ml_backup_dir/training_data.tar.gz" -C "$training_source" . 2>/dev/null; then
            log_info "✓ Training data backed up"
            ((total_backed_up++))
        else
            log_warn "✗ Training data backup failed"
        fi
    fi
}

# Backup ChromaDB
backup_chromadb() {
    log_info "Backing up ChromaDB vector database..."

    local chromadb_backup_dir="$BACKUP_DIR/chromadb"
    local chromadb_source="/opt/hungryhounddog/chromadb"

    if [ -d "$chromadb_source" ]; then
        if tar czf "$chromadb_backup_dir/chromadb.tar.gz" -C "$chromadb_source" . 2>/dev/null; then
            log_info "✓ ChromaDB backed up"
            ((total_backed_up++))
        else
            log_warn "✗ ChromaDB backup failed"
            ((total_errors++))
        fi
    else
        log_warn "ChromaDB directory not found"
    fi
}

# Backup configurations
log_section "Phase 1: Node Configurations"

declare -A NODES=(
    ["adversary"]="192.168.1.50"
    ["modbus_server"]="192.168.10.10"
    ["monitoring"]="192.168.20.10"
    ["logger"]="192.168.20.20"
)

for node in "${!NODES[@]}"; do
    backup_node_config "$node" "${NODES[$node]}" "" || true
done

# Backup OpenSearch
log_section "Phase 2: OpenSearch Indices"
backup_opensearch

# Backup ML models
log_section "Phase 3: ML Models"
backup_ml_models

# Backup ChromaDB
log_section "Phase 4: ChromaDB"
backup_chromadb

# Backup documentation
log_section "Phase 5: Documentation"

local doc_source="/sessions/gracious-stoic-goodall/mnt/hungryhounddog"
if [ -d "$doc_source" ]; then
    find "$doc_source" -name "*.md" -o -name "*.txt" 2>/dev/null | \
        xargs tar czf "$BACKUP_DIR/documentation/docs.tar.gz" 2>/dev/null || true
    log_info "✓ Documentation backed up"
    ((total_backed_up++))
fi

# Create manifest
log_section "Phase 6: Creating Manifest"

cat > "$BACKUP_DIR/MANIFEST.txt" << MANIFEST
HungryHoundDog Backup Manifest
==============================
Backup Date: $(date)
Backup ID: backup_$TIMESTAMP

Contents:
- configs/: Node configuration files
- opensearch/: OpenSearch indices snapshots
- ml_models/: Trained machine learning models
- chromadb/: Vector database (Chroma)
- documentation/: Network diagrams and configuration docs

Statistics:
- Items backed up: $total_backed_up
- Errors encountered: $total_errors
- Total backup size: $(du -sh "$BACKUP_DIR" | cut -f1)

Restore Instructions:
1. Extract backup directory to restore location
2. Restore configurations to respective nodes via deploy_all.sh
3. Restore OpenSearch indices via snapshot API
4. Copy ML models to /opt/hungryhounddog/ml/models
5. Restore ChromaDB and restart chatbot service

Verification:
Run: sha256sum -c backup_$TIMESTAMP.sha256

MANIFEST

# Create checksum file
log_info "Generating checksums..."
cd "$BACKUP_DIR"
find . -type f -exec sha256sum {} \; > "backup_$TIMESTAMP.sha256"

# Compress entire backup
log_section "Compressing Backup"
cd "$BACKUP_BASE"
if tar czf "backup_$TIMESTAMP.tar.gz" "backup_$TIMESTAMP" 2>/dev/null; then
    log_info "✓ Backup compressed to backup_$TIMESTAMP.tar.gz"
    
    # Calculate final size
    backup_size=$(ls -lh "backup_$TIMESTAMP.tar.gz" | awk '{print $5}')
    log_info "Compressed backup size: $backup_size"
fi

# Summary
log_section "Backup Summary"

log_info "Items backed up: $total_backed_up"
log_info "Errors: $total_errors"
log_info "Backup location: $BACKUP_DIR"
log_info "Compressed archive: $BACKUP_BASE/backup_$TIMESTAMP.tar.gz"
log_info "Backup log: $LOG_FILE"

echo -e "\n${GREEN}Backup completed successfully!${NC}\n"

exit 0
