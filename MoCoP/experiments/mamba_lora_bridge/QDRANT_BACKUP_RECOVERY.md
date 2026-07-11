# Qdrant Backup Recovery Procedure (P0-2)

**Author:** P0 security lane (OpenCLAW #138)  
**Date:** 2026-07-06  
**Status:** Active — encrypted backups enabled  
**GPG Key ID:** `CACD642C2DE15EEE32D815B65E335ED4C822C8C4`

---

## Overview

Since P0-2 (2026-07-06), all Qdrant backups are **encrypted with GPG before upload to Google Drive**. This protects the memory store at rest in cloud storage.

- **Backup script:** `/root/backup_qdrant.sh` on NUC Qdrant LXC 101
- **Backup location (encrypted):** `gdrive:backups/qdrant/*.snapshot.gpg`
- **Backup location (local):** `/root/backups/` on LXC 101 (both `.snapshot` and `.gpg` files, 7-day retention)
- **Encryption:** GPG (GnuPG 2.2.40), RSA 4096-bit
- **Key location:** `/root/qdrant_backup_gpg_key.asc` on LXC 101 (private key export)
- **Backup frequency:** Weekly Sunday 03:00 (cron)

---

## Encryption Key Custody

### Primary key location
The GPG key lives in the GPG keyring on LXC 101:
```bash
ssh root@192.168.2.55
pct exec 101 -- gpg --list-keys
# Should show: qdrant-backup@mocop.local
```

### Exported key backup
Private key exported to `/root/qdrant_backup_gpg_key.asc` on LXC 101.

**THIS KEY MUST BE BACKED UP SEPARATELY.** Without it, encrypted backups on Google Drive are permanently inaccessible.

### Recommended key backup locations
1. **Laura's password manager** (1Password / Bitwarden) — store `/root/qdrant_backup_gpg_key.asc` content as secure note
2. **Offline USB drive** — copy key file, store with NUC documentation
3. **Encrypted repo backup** — NOT committed to git (listed in `.gitignore`), but stored in Laura's encrypted local backup

To retrieve the key for backup:
```bash
ssh root@192.168.2.55 "pct exec 101 -- cat /root/qdrant_backup_gpg_key.asc"
```

---

## Disaster Recovery Scenarios

### Scenario 1: NUC failure, LXC lost, need to restore Qdrant from Google Drive

**Prerequisites:**
- Access to Google Drive `backups/qdrant/`
- GPG private key (`qdrant_backup_gpg_key.asc`)
- Fresh Qdrant instance (running, empty collections)

**Steps:**

1. **Download latest encrypted backup from Google Drive:**
   ```bash
   # On recovery machine with rclone configured
   rclone copy gdrive:backups/qdrant/ ./qdrant_recovery/ --include "*.gpg"
   ls -lh ./qdrant_recovery/
   # Pick the most recent .snapshot.gpg file
   ```

2. **Import GPG key on recovery machine:**
   ```bash
   # Copy qdrant_backup_gpg_key.asc from password manager or backup location
   gpg --import qdrant_backup_gpg_key.asc
   gpg --list-keys  # Verify qdrant-backup@mocop.local appears
   ```

3. **Decrypt snapshot:**
   ```bash
   gpg --decrypt --output exocortex-recovered.snapshot \
       qdrant_recovery/exocortex-*.snapshot.gpg
   # Should decrypt without passphrase (key has no passphrase)
   ls -lh exocortex-recovered.snapshot  # ~140MB for exocortex collection
   ```

4. **Restore snapshot to Qdrant over verified TLS:**
   ```bash
   # Use the recovery target's HTTPS URL, public CA, and WRITE key.  Do not use
   # curl -k, plaintext HTTP, or a read-only key during recovery.
   export QDRANT_URL="https://<QDRANT_HOST>:6333"
   export QDRANT_CA_CERT="/secure/path/to/qdrant-lan-root-ca.crt"
   export QDRANT_API_KEY="$(< /secure/path/to/qdrant-write-key)"

   curl --fail --cacert "$QDRANT_CA_CERT" -X PUT \
        "$QDRANT_URL/collections/exocortex/snapshots/upload" \
        -H "api-key: $QDRANT_API_KEY" \
        -H "Content-Type: application/octet-stream" \
        --data-binary @exocortex-recovered.snapshot

   # Verify collection restored
   curl --fail --cacert "$QDRANT_CA_CERT" \
        -H "api-key: $QDRANT_API_KEY" \
        "$QDRANT_URL/collections/exocortex" | jq '.result.points_count'
   ```

---

### Scenario 2: Accidental collection deletion, need point-in-time restore

**Prerequisites:**
- Qdrant instance still running
- Access to local backups on LXC 101 (`/root/backups/`) or Google Drive

**Steps:**

1. **SSH to LXC 101:**
   ```bash
   ssh root@192.168.2.55
   pct exec 101 -- bash
   ```

2. **List available backups:**
   ```bash
   ls -lh /root/backups/*.snapshot.gpg
   # Pick the snapshot from before the deletion
   ```

3. **Decrypt locally:**
   ```bash
   cd /root/backups
   gpg --decrypt --output exocortex-restore.snapshot \
       exocortex-<TIMESTAMP>.snapshot.gpg
   ```

4. **Restore via the verified Qdrant API:**
   ```bash
   # The local Qdrant LXC is TLS-only. Use its LAN name/IP that matches the
   # certificate SAN, not localhost unless localhost is explicitly in that SAN.
   export QDRANT_URL="https://192.168.2.191:6333"
   export QDRANT_CA_CERT="/secure/path/to/qdrant-lan-root-ca.crt"
   export QDRANT_API_KEY="$(< /secure/path/to/qdrant-write-key)"

   curl --fail --cacert "$QDRANT_CA_CERT" -X PUT \
        "$QDRANT_URL/collections/exocortex/snapshots/upload" \
        -H "api-key: $QDRANT_API_KEY" \
        -H "Content-Type: application/octet-stream" \
        --data-binary @exocortex-restore.snapshot

   # Verify restored
   curl --fail --cacert "$QDRANT_CA_CERT" \
        -H "api-key: $QDRANT_API_KEY" \
        "$QDRANT_URL/collections/exocortex" | jq '.result.points_count'
   ```

---

### Scenario 3: Lost GPG key, encrypted backups on Google Drive are inaccessible

**If key is backed up:**
- Retrieve from password manager / offline USB / encrypted local backup
- Import per Scenario 1 step 2

**If key is permanently lost:**
- **Encrypted Google Drive backups are unrecoverable** (by design — this is what encryption does)
- **Fallback:** Check if any local unencrypted snapshots exist on LXC 101:
  ```bash
  ssh root@192.168.2.55 "pct exec 101 -- ls -lh /root/backups/*.snapshot"
  # Local .snapshot files (unencrypted) are kept for 7 days
  ```
- **If local unencrypted backups also gone:** Data loss. Qdrant must be rebuilt from application logs / other sources.

**Prevention:** Back up the GPG key to multiple secure locations immediately after P0-2 deployment.

---

### Scenario 4: Corrupt encrypted backup on Google Drive

**Symptoms:**
- `gpg --decrypt` fails with "invalid packet" or "checksum error"
- File size is 0 or significantly smaller than expected

**Steps:**

1. **Try an older backup:**
   ```bash
   rclone ls gdrive:backups/qdrant/ | grep snapshot.gpg | sort -r
   # Pick second-most-recent backup
   rclone copy gdrive:backups/qdrant/<OLDER_SNAPSHOT>.gpg ./
   gpg --decrypt <OLDER_SNAPSHOT>.gpg
   ```

2. **If all Google Drive backups are corrupt:**
   - Check local backups on LXC 101 (7-day retention)
   - Verify backup script is running correctly:
     ```bash
     ssh root@192.168.2.55 "pct exec 101 -- bash /root/backup_qdrant.sh"
     tail /root/backup_qdrant.log
     ```

3. **If corruption persists in new backups:**
   - GPG key may be damaged
   - Re-export key: `gpg --export-secret-keys --armor qdrant-backup@mocop.local`
   - Compare with backed-up key
   - If different, restore key from backup and re-run backup script

---

## Encryption Key Rotation (when needed)

**When to rotate:**
- Key compromise suspected
- Routine rotation (recommended every 2 years)
- Changing backup encryption strategy

**Steps:**

1. **Generate new GPG key:**
   ```bash
   ssh root@192.168.2.55
   pct exec 101 -- bash
   gpg --batch --gen-key << EOF
   %no-protection
   Key-Type: RSA
   Key-Length: 4096
   Name-Real: Qdrant Backup Encryption
   Name-Email: qdrant-backup@mocop.local
   Expire-Date: 0
   EOF
   ```

2. **Export new key:**
   ```bash
   NEW_KEY_ID=$(gpg --list-keys qdrant-backup@mocop.local | grep "^pub" | tail -1 | awk '{print $2}' | cut -d'/' -f2)
   gpg --export-secret-keys --armor $NEW_KEY_ID > /root/qdrant_backup_gpg_key_new.asc
   ```

3. **Update backup script if needed** (script uses email `qdrant-backup@mocop.local`, so if the new key has the same email, no script change needed)

4. **Back up new key** to password manager / USB / secure locations

5. **Test new key:**
   ```bash
   echo "test" | gpg --encrypt --recipient qdrant-backup@mocop.local | gpg --decrypt
   ```

6. **Revoke old key (optional, after confirming new key works):**
   ```bash
   OLD_KEY_ID=CACD642C2DE15EEE32D815B65E335ED4C822C8C4
   gpg --delete-secret-keys $OLD_KEY_ID
   gpg --delete-keys $OLD_KEY_ID
   ```

7. **Note:** Old encrypted backups on Google Drive remain encrypted with the old key. Keep old key backed up until those old backups expire or are no longer needed.

---

## Verification & Testing

### Test encryption (monthly recommended)

```bash
ssh root@192.168.2.55
pct exec 101 -- bash << 'EOF'
cd /root/backups
# Pick a recent encrypted backup
LATEST_ENC=$(ls -t *.snapshot.gpg | head -1)
echo "Testing decryption of: $LATEST_ENC"

# Decrypt
gpg --decrypt --output /tmp/test_decrypt.snapshot "$LATEST_ENC"

if [ $? -eq 0 ]; then
    SIZE=$(ls -lh /tmp/test_decrypt.snapshot | awk '{print $5}')
    echo "✓ Decryption successful, snapshot size: $SIZE"
    rm /tmp/test_decrypt.snapshot
else
    echo "✗ Decryption FAILED — investigate immediately"
    exit 1
fi
EOF
```

### Verify Google Drive backup exists

```bash
rclone ls gdrive:backups/qdrant/ | grep snapshot.gpg | tail -5
# Should show encrypted backups from recent weeks
```

---

## Backup Script Details

**Location:** `/root/backup_qdrant.sh` on LXC 101  
**Original (unencrypted):** Backed up to `/root/backup_qdrant.sh.backup`  
**Cron:** `0 3 * * 0` (Sunday 03:00, runs as root on LXC 101)

**What the script does:**
1. Creates Qdrant snapshot via API (`POST /collections/exocortex/snapshots`)
2. Downloads snapshot locally
3. **Encrypts snapshot with GPG** (`gpg --encrypt --recipient qdrant-backup@mocop.local`)
4. Uploads **encrypted .gpg file** to Google Drive via rclone
5. Cleans up local files older than 7 days (both `.snapshot` and `.gpg`)
6. Deletes old server-side Qdrant snapshots (keeps latest 3)

**Logs:** `/root/backup_qdrant.log` on LXC 101

---

## Key Management Checklist

- [ ] GPG private key exported to `/root/qdrant_backup_gpg_key.asc`
- [ ] Key backed up in Laura's password manager
- [ ] Key backed up on offline USB drive
- [ ] Test decryption performed successfully
- [ ] Google Drive encrypted backups verified present
- [ ] Backup script cron confirmed running (check `/root/backup_qdrant.log` for recent entries)
- [ ] Recovery procedure tested at least once (decrypt a backup, verify it opens)
- [ ] Old unencrypted backups on Google Drive purged (after confirming encrypted backups work)

---

*The memory is encrypted at rest. The key is not. Guard the key.*

— P0 security lane, 2026-07-06
