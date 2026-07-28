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
| bot-coin | 매시 :05 (24시간) | 코인은 휴장 없음 |
| bot-swing | 평일 09:05 | 공휴일은 봇이 자체 스킵 (KIS 휴장일 API + 캐시) |
| bot-swing-monitor | 평일 09:00~15:30 /30분 | 1회 점검 모드, 장시간·휴장 자체 판정 |
| trading-backup | 매일 23:50 | data/ → /var/backups/trading (30개 보관) |

각 봇 사이클 뒤에 dashboard-build가 자동 실행되어 대시보드가 갱신된다.

**예산**: 코인봇은 unit 파일의 `--budget`(기본 1,000만원)이 상한 — 첫 실행 때 원장이
이 값으로 생성되므로 **가동 전에 원하는 값으로 확정**할 것 (이후 변경은 state 파일 수정).
스윙봇은 코드 상수 `INITIAL_CASH`(100만원). 봇은 계좌 잔고를 조회하지 않고 원장 현금만
쓰므로, 계좌의 기존 보유 자산·예수금은 예산과 무관하게 불가침이다.

## 4. 대시보드 접근 (Tailscale — 포트 개방 없음)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                      # 브라우저로 로그인 승인
# 정적 파일 서빙 (tailnet 안에서만 접근 가능)
sudo tee /etc/systemd/system/dashboard-serve.service <<'EOF'
[Unit]
Description=대시보드 정적 서빙 (tailnet 전용)
[Service]
User=trading
WorkingDirectory=/opt/stock-trade-bot/data/reports
ExecStart=/usr/bin/python3 -m http.server 8080 --bind 0.0.0.0
Restart=always
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now dashboard-serve
# 방화벽: tailscale0 인터페이스만 8080 허용 (공인망 차단)
sudo ufw allow in on tailscale0 to any port 8080
sudo ufw deny 8080
```

폰/노트북에 Tailscale 앱 설치 후 `http://<서버 tailnet IP>:8080/dashboard.html`

## 5. 운영

```bash
journalctl -u bot-coin.service -n 50          # 봇 로그
sudo -u trading bash -lc 'cd /opt/stock-trade-bot && git pull && uv sync'   # 버전업 (data/ 무관)
```

- 재부팅/회수 후: 타이머 `Persistent=true`가 놓친 사이클을 따라잡음. 상태는 `data/state/`에 파일로 있어 유실 없음
- 복구: 새 서버에 1~3 재실행 후 `/var/backups/trading/data-최신.tar.gz`를 `/opt/stock-trade-bot/`에 풀면 끝
