#!/usr/bin/env bash
# data/ 일일 백업 — 상태·거래내역·리포트 전부 (몇 MB 수준)
# 오프사이트가 필요하면 마지막 rclone 줄의 주석을 해제하고 리모트를 설정할 것.
set -euo pipefail

REPO=/opt/stock-trade-bot
DEST=/var/backups/trading
KEEP=30

mkdir -p "$DEST"
STAMP=$(date +%Y%m%d)
tar -C "$REPO" -czf "$DEST/data-$STAMP.tar.gz" data
# 최근 KEEP개만 유지
ls -1t "$DEST"/data-*.tar.gz | tail -n +$((KEEP + 1)) | xargs -r rm --
echo "백업 완료: $DEST/data-$STAMP.tar.gz"

# rclone copy "$DEST/data-$STAMP.tar.gz" remote:trading-backup/   # 오브젝트 스토리지 업로드 (선택)
