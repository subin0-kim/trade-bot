# 리눅스 서버 배포 절차

전제: Ubuntu 22.04+ 일반 VM (스팟/선점형 금지 — 삭제 시 디스크 소실), 1vCPU/1GB면 충분.

## 1. 기본 셋업

```bash
# 타임존 — 필수! 봇 로직이 로컬시간 기준 (쇼크 창 10~11시, 09시 청산, 장시간 판정)
sudo timedatectl set-timezone Asia/Seoul

# 전용 사용자 + 코드
sudo useradd -m -s /bin/bash trading
sudo git clone https://github.com/subin0-kim/trade-bot.git /opt/stock-trade-bot
sudo chown -R trading:trading /opt/stock-trade-bot

# uv 설치 (trading 사용자로)
sudo -u trading bash -lc 'curl -LsSf https://astral.sh/uv/install.sh | sh'
sudo -u trading bash -lc 'cd /opt/stock-trade-bot && uv sync'
```

## 2. 인증파일 (절대 git에 넣지 말 것)

```bash
sudo mkdir -p /etc/trading
# 로컬 PC에서 복사: scp D:/kis/config/kis_devlp.yaml D:/upbit/config/upbit.yaml server:/tmp/
sudo mv /tmp/kis_devlp.yaml /tmp/upbit.yaml /etc/trading/
sudo chown -R trading:trading /etc/trading && sudo chmod 600 /etc/trading/*
```

- KIS 토큰 캐시는 설정 yaml 옆에 자동 생성됨 (`/etc/trading/tokens/`) — 첫 실행 시 재발급
- **업비트 개발자센터에서 서버 공인 IP를 허용 IP에 등록할 것** (미등록 시 인증 실패)

## 3. systemd 타이머 등록

```bash
sudo cp /opt/stock-trade-bot/deploy/systemd/* /etc/systemd/system/
sudo chmod +x /opt/stock-trade-bot/deploy/backup.sh
sudo systemctl daemon-reload
sudo systemctl enable --now bot-coin.timer bot-swing.timer bot-swing-monitor.timer trading-backup.timer
systemctl list-timers          # 다음 실행 시각 확인
```

| 타이머 | 주기 | 비고 |
|---|---|---|
| bot-coin | 매시 :05 (24시간) | **⚠️ LIVE 실계좌** (`--live --yes`), 코인은 휴장 없음 |
| bot-swing | 평일 09:05 | dry-run. 공휴일은 봇이 자체 스킵 (KIS 휴장일 API + 캐시) |
| bot-swing-monitor | 평일 09:00~15:30 /30분 | 1회 점검 모드, 장시간·휴장 자체 판정 |
| trading-backup | 매일 23:50 | data/ → /var/backups/trading (30개 보관) |

각 봇 사이클 뒤에 dashboard-build가 자동 실행되어 대시보드가 갱신된다.

**예산**: 코인봇은 unit 파일의 `--budget`(기본 1,000만원)이 상한 — 첫 실행 때 원장이
이 값으로 생성되므로 **가동 전에 원하는 값으로 확정**할 것 (이후 변경은 state 파일 수정).
스윙봇은 코드 상수 `INITIAL_CASH`(100만원). 봇은 계좌 잔고를 조회하지 않고 원장 현금만
쓰므로, 계좌의 기존 보유 자산·예수금은 예산과 무관하게 불가침이다.

## 3.5 코인봇 실전(LIVE) 전환 절차

봇 원장에는 생성 당시 모드(`dry-run`/`live`)가 기록되며, **실행 모드와 다르면 봇이
기동을 거부한다** (dry-run 가상 포지션을 실계좌에서 팔아버리는 사고 방지).
전환 순서:

```bash
sudo systemctl stop bot-coin.timer

# 1. dry-run 원장·이벤트 보관 (전방 검증 기록 — 삭제 금지)
sudo -u trading mv /opt/stock-trade-bot/data/state/bot-coin.json \
                   /opt/stock-trade-bot/data/state/bot-coin.json.dry-run.bak
sudo -u trading cp /opt/stock-trade-bot/data/events/bot-coin.jsonl \
                   /opt/stock-trade-bot/data/events/bot-coin.dry-run.jsonl
# 이벤트 로그는 이어서 써도 됨 — entry/exit/equity에 mode(LIVE/DRY-RUN)가 찍힌다

# 2. 계좌 준비 확인
#    - 업비트 개발자센터: API 키에 '주문' 권한 + 서버 공인 IP 등록 여부
#    - KRW 잔고 ≥ --budget (부족하면 봇이 경고 로그를 남기고 매수가 실패한다)

# 3. 갱신된 unit 반영 (--live --yes 포함) 후 재시작
sudo cp /opt/stock-trade-bot/deploy/systemd/bot-coin.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start bot-coin.timer

# 4. 첫 사이클 수동 실행 + 로그 확인 (타이머 기다릴 필요 없음)
sudo systemctl start bot-coin.service
journalctl -u bot-coin.service -n 50
```

첫 실행 때 원장이 `--budget` 현금으로 새로 생성된다. 첫 사이클에서 레짐이 초록불이면
곧바로 코어(BTC/ETH) 매수가 나가는 게 정상 동작이다.

**긴급 정지**: `sudo systemctl stop bot-coin.timer` — 이후 보유분을 정리하려면
수동으로 1사이클씩 돌리거나 업비트 앱에서 직접 매도 후 원장(state 파일)에서 해당
포지션을 제거한다 (원장에 남겨두면 봇이 이미 없는 코인을 팔려고 시도한다).

## 4. 대시보드 접근 (Tailscale + 비밀번호 — 포트 개방 없음)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                      # 브라우저로 로그인 승인
TSIP=$(tailscale ip -4)

# nginx + Basic Auth (비밀번호는 안전한 곳에 보관)
sudo apt-get install -y nginx apache2-utils
sudo rm -f /etc/nginx/sites-enabled/default          # 공개 80 포트 기본 사이트 제거
sudo htpasswd -cB /etc/nginx/.htpasswd-dashboard <아이디>
sudo tee /etc/nginx/sites-available/dashboard <<EOF
# listen이 tailnet IP라 공인망에서는 접속 자체가 불가 (ufw 없이도 안전)
server {
    listen ${TSIP}:8080;
    root /opt/stock-trade-bot/data/reports;
    index dashboard.html;
    auth_basic "Trading Dashboard";
    auth_basic_user_file /etc/nginx/.htpasswd-dashboard;
    location / { try_files \$uri \$uri/ =404; add_header Cache-Control "no-store"; }
}
EOF
sudo ln -sf /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/
# 부팅 시 tailscaled → nginx 순서 보장 (tailnet IP 바인딩 실패 방지)
sudo mkdir -p /etc/systemd/system/nginx.service.d
printf '[Unit]\nAfter=tailscaled.service\nWants=tailscaled.service\n\n[Service]\nRestart=on-failure\nRestartSec=5\n' \
  | sudo tee /etc/systemd/system/nginx.service.d/tailscale-order.conf
sudo systemctl daemon-reload && sudo nginx -t && sudo systemctl enable --now nginx

# 검증: 401(비밀번호 없이) / 200(비밀번호) / 공인 IP는 연결 거부
curl -s -o /dev/null -w "%{http_code}\n" http://${TSIP}:8080/
```

폰/노트북에 Tailscale 앱 설치(같은 계정 로그인) 후 `http://<서버 tailnet IP>:8080/` — 아이디/비밀번호 입력

## 5. 운영

```bash
journalctl -u bot-coin.service -n 50          # 봇 로그
sudo -u trading bash -lc 'cd /opt/stock-trade-bot && git pull && uv sync'   # 버전업 (data/ 무관)
```

- 재부팅/회수 후: 타이머 `Persistent=true`가 놓친 사이클을 따라잡음. 상태는 `data/state/`에 파일로 있어 유실 없음
- 복구: 새 서버에 1~3 재실행 후 `/var/backups/trading/data-최신.tar.gz`를 `/opt/stock-trade-bot/`에 풀면 끝
