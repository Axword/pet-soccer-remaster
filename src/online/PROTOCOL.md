# Pet Soccer Online 1v1 transport prototype

This folder contains a new, engine-independent TCP lobby and relay. Both game peers open an outbound TCP connection to the same broker. It never calls the game's disabled native networking APIs.

## Run

Prepare the isolated developer workspace as described in
[ONLINE_BUILD.md](../../docs/ONLINE_BUILD.md). Do not start the source-only
copy directly: server databases and generated helpers belong in ignored build/.
The staged broker can be run explicitly with a test database:

```text
build/online/payload/online/runtime/python.exe -I -u build/online/payload/online/broker.py --bind 127.0.0.1 --port 27889 --db build/online/manual-test.sqlite3
```

The shipped default local server uses loopback27888, and the explicit LAN
helper uses27889 with a separate ledger. No firewall or router changes are made.
The broker has no accounts, authentication, encryption or NAT traversal.
Use trusted peers; this is a self-host prototype, not a hosted public service.
The staged/installed script defaults to data/leaderboard.sqlite3 beside itself;
the launcher and LAN helper supply an explicit writable --db path. API Broker()
used by tests defaults to an in-memory database. Restart retains completed
results but abandons unfinished matches; rooms cannot resume after restart.

## Java 1.3 API

`../java/CXOnlineTransport.java` is a default-package class. Compile it into the isolated game code archive together with the menu and match adapter. It depends only on the game's existing Java 1.3 runtime. `classes/TransportProbe*` are test programs and should not be inserted into the game archive.

```java
CXOnlineTransport.start(server, 27888, nickname, "GMWL-6fbcaedb-online5");
CXOnlineTransport.listRooms();
CXOnlineTransport.createRoom("My room");
CXOnlineTransport.joinRoom(roomId);
CXOnlineTransport.setTeams(hostTeam, guestTeam);
CXOnlineTransport.setReady(true);
CXOnlineTransport.requestSelfStats();
CXOnlineTransport.requestLeaderboard();
CXOnlineTransport.requestPause(); // only during an active Online match
CXOnlineTransport.leaveRoom();
CXOnlineTransport.stop();
```

All commands enqueue bounded work; caller/main thread performs no DNS, connect, read or write. `setTeams` updates only the caller's own team; the broker ignores the other side's proposed team. A real change clears both ready flags. Valid animal IDs are stock 0..11 and additional IDs 30, 37, 44, 51, 58. Both ready starts a match once. No late joins, host migration or room resume after disconnect.

The menu/main pump calls `Event[] drainEvents()`. Fields are public: `type`, `message`, `roomId`, `roomName`, `version`, `hostNick`, `guestNick`, `hostReady`, `guestReady`, `isHost`, `started`, `matchId`, `hostTeam`, `guestTeam`, `rooms`. Relevant fields are populated for each event, not a full implicit state copy. `START` includes version, roomId, matchId, teams, isHost and started. `Room` list entries have `id`, `name`, `version`, host/guest nicknames, readiness, started, teams and matchId. Events: CONNECTING, CONNECTED, DISCONNECTED, ERROR, ROOMS, LOBBY, LEFT, START.

Statistics events are `LEADERBOARD=11`, `SELF_STATS=12`, `RESULT=13`. `Event.leaderboard` is `PlayerStats[]`; `Event.playerStats` is `PlayerStats`; `RESULT` carries `Event.matchId` and `Event.resultStatus`. `PlayerStats` has public `String nick` and `int rank,wins,draws,losses,games,points,winRate100`. `winRate100` is the truncated percentage multiplied by 100 (3333 means 33.33%). `getLeaderboard()` and `getSelfStats()` return defensive copies of the latest responses without network or disk access. They return null until a real response on the current connection; a received zero-length ranking means no completed games. Room exit retains cached stats; connection loss clears them. Requests enqueue bounded work and never perform socket or SQLite operations on the caller thread. Repeated requests of each statistics type merge into one pending refresh; the background writer waits at least 300ms after that type's previous send. A request arriving inside this interval is deferred, preserving the next fresh response. At most two extra pending flags exist. Room cleanup retains pending refreshes, while reconnect clears them. Thus RESULT/Show/LEFT refresh bursts do not fill the control queue or produce ordinary broker query-limit errors.

Leaderboard entries include only players with completed games, up to 50. Ranking is descending `points=3*wins+draws`, then wins, exact win fraction, then ascending normalized nickname. Self stats include the real rank even beyond 50, or rank 0 and zero W/D/L before any completed game. `games=wins+draws+losses`; `winRate100=10000*wins/games` using integer division, or zero for zero games. Identity is the existing trusted prototype ASCII pseudonym, trimmed and lowercased for comparisons, length 1..48 printable ASCII characters. First-seen spelling is retained for display. Two equal normalized nicknames cannot join the same match; this is not account authentication.

The match adapter uses `isConnected()`, `isHost()`, `isGuest()`, `isMatchStarted()`, `getRoomId()`, `getMatchId()`, `getHostTeam()`, `getGuestTeam()`. It calls `boolean sendSnapshot(byte[])` only as host, and `boolean sendInput(int[])` only as guest. Inputs are 1..32 signed integers; the transport prepends an integer count. `int[] pollInput()` consumes one input packet on the host; `byte[] pollSnapshot()` returns the newest snapshot on the guest. Raw `sendInput(byte[])` and `pollInputBytes()` are also available. Payloads are opaque to the broker. **Snapshot/input mailboxes are separate from `drainEvents()`**; SNAPSHOT/INPUT constants and Event.data exist for compatibility but payload events are not emitted. A false send result means invalid state, payload limit, or a full queue; the caller must stop/retry according to match semantics rather than assume delivery.

The network threads update transport-only state and never call engine or menu code. Menu and match must perform game object work on their existing game thread. Room exit, guest loss and connection loss clear match payload mailboxes. START clears inbound mailboxes before enabling the match. The match payload format must include its own matchId/sequence/version and validate numerical state; the broker cannot validate game simulation.

## Shared 15-second pause

`boolean requestPause()` queues a request only for a connected, started match;
it does not locally pause the game before the authoritative reply. False means
invalid match state or a failed bounded enqueue. Repeated local calls while
already paused or within one second of the previous pending request return true
without adding another packet. This also bounds held-key requests before the
first acknowledgement.

`boolean isPaused()`, `int getPauseRemainingMillis()` and `int getPauseMatchId()`
are cache-only synchronized getters for the engine/UI thread. Remaining time
is in 0..15000ms, with zero meaning resume. The Java reader stores an absolute
local deadline on receipt of the server state; its countdown expires locally
even if an explicit resume packet is delayed. A later matching server resume
also clears it. The match ID remains available after resume until that match
ends; room/connection reset and START clear all pause state.

The optional event is `PAUSE=14`, with `Event.matchId`, `Event.paused` and
`Event.remainingMillis`; it coalesces by type. Engine integration must read the
cache every frame and stop/resume gameplay only on its existing engine thread,
keeping transport pumping and pings active. No engine function is called by
the reader, writer or broker.

Either started-room participant can request one shared pause. The broker uses
one event-loop monotonic deadline and one cancellable timer per paused room.
It broadcasts the same match ID and remaining duration to both participants
immediately; repeated requests during the interval do not extend the deadline,
replace the timer, or enqueue duplicate states. After 15 seconds the server
broadcasts resume to both even with no further gameplay traffic. A request
after the previous pause has ended may start a new pause. Waiting rooms,
outsiders and completed/conflicted matches cannot pause. Leaving, disconnect,
room destruction and terminal result cancel the timer. Stale timers cannot
touch a newer match in the same room.

The broker silently discards guest gameplay INPUT while the deadline is active.
SNAPSHOT, results, ping and control traffic continue. On entering pause the Java
reader discards inbound gameplay mailboxes and unsent outbound INPUT, while
preserving ordered control/final-state/result packets. The match adapter must
also clear/neutralize held gameplay actions and preserve its input-counter
baselines so pre-pause button edges do not replay after resume. The transport
does not itself freeze engine timers, physics, audio or native UI.

The launcher may probe `QUERY_CAPABILITIES` after HELLO without entering a room.
`CAPABILITIES` returns an int32 bit mask: 1 statistics, 2 shared pause,
4 expansion including species58. The current broker returns7 and the launcher
requires all three bits. The game build/room ID is now online5.

## Wire format, version 1

TCP frames contain a 4-byte **unsigned big endian length**, followed by a one-byte type and body. Length includes type, excludes the 4-byte prefix; 1..65536. Integers are signed big endian int32 unless noted. Strings are uint16 byte length + standard UTF-8 bytes (not Java modified UTF). Booleans are one byte 0/1. Strings in HELLO and CREATE are nonempty and contain no ASCII control characters. Limits are encoded bytes: nickname 48, build version 80, room name 96. Maximum opaque payload is 60000 bytes.

| Type | Direction | Body |
| --- | --- | --- |
| 1 HELLO | client→broker, first frame | uint16 protocol=1, string nickname, string buildVersion |
| 2 WELCOME | broker→client | int peerId |
| 3 LIST | client→broker | empty |
| 4 ROOMS | broker→client | uint16 count, then `room` repeated count times |
| 5 CREATE | client→broker | string roomName |
| 6 JOIN | client→broker | int roomId |
| 7 LEAVE | client→broker | empty |
| 8 READY | client→broker | bool ready |
| 9 LOBBY | broker→client | `room`, bool recipientIsHost |
| 10 LEFT | broker→client | empty or string reason |
| 11 ERROR | broker→client | string explanation |
| 12 SNAPSHOT | host→broker→guest | 1..60000 opaque bytes, only after START |
| 13 INPUT | guest→broker→host | 1..60000 opaque bytes, only after START |
| 14 PING | client→broker | empty |
| 15 PONG | broker→client | empty |
| 16 TEAMS | client→broker | int hostTeam, int guestTeam; only own side applied |
| 17 START | broker→each peer | int matchId, int hostTeam, int guestTeam, bool recipientIsHost |
| 18 GET_LEADERBOARD | client→broker | empty |
| 19 LEADERBOARD | broker→client | uint16 count (0..50), then `stats` repeated count times |
| 20 GET_SELF_STATS | client→broker | empty; only the caller's nickname is queried |
| 21 SELF_STATS | broker→client | `stats` |
| 22 RESULT | client→broker | int matchId, int hostGoals, int guestGoals (each 0..999) |
| 23 RESULT_STATUS | broker→client | int matchId, int status (1 pending, 2 recorded, 3 conflict) |
| 24 PAUSE_REQUEST | client→broker | empty; active match participant only |
| 25 PAUSE_STATE | broker→both participants | int matchId, bool paused, int remainingMs (1..15000 when paused, 0 when resumed) |
| 26 QUERY_CAPABILITIES | client→broker | empty; after HELLO, no room required |
| 27 CAPABILITIES | broker→client | int bitMask (1 statistics, 2 pause, 4 expansion58; current value 7) |

`room` is: int id, string name, string buildVersion, string hostNick, string guestNick (empty if vacant), bool hostReady, bool guestReady, bool started, int hostTeam, int guestTeam, int matchId. LIST includes only exact build-version matches. JOIN also enforces that equality. Wire protocol mismatch closes during handshake. Every room has exactly one host and at most one guest. Match IDs are positive signed int32 allocated by SQLite AUTOINCREMENT at START, never reused across restarts of the same database. Exhausting the int32 capacity refuses START. Transport always clears local room state on connection loss.

`stats` is: string nick, int rank, int wins, int draws, int losses, int games, int points, int winRate100. All ints are nonnegative signed int32. The Java reader verifies the counts and derived values before accepting a response.

Ordering: READY that completes readiness sends LOBBY(started=true) followed by START to each peer over that peer's TCP stream. Java flips `isMatchStarted` only on START. Host disconnect/LEAVE deletes the room and sends LEFT to guest. Guest disconnect/LEAVE removes the guest, cancels started/readiness and sends host a new LOBBY(started=false); host stays in the waiting room.

Only the match adapter's actual terminal full-time path calls `submitMatchResult(matchId,hostGoals,guestGoals)`. Scores must use stable participant identity (host/guest), regardless of halftime team-array swaps. The broker does not infer completion or score from opaque game snapshots. It accepts exactly one immutable attestation per connected participant for the current server-started match. Matching host and guest attestations atomically mark the match completed and update both W/D/L records once. A changed attestation or disagreement makes an unfinished result terminally conflicted and gives neither player a game. Repeating a recorded matching result returns status 2 without another increment; a conflicting replay returns ERROR. First receipt returns status 1 to its sender; status 2/3 goes to both. Status 2 is followed by fresh SELF_STATS for both.

The host calls `sendFinalSnapshot(byte[])` before submitting its result. This special API sends the still-opaque SNAPSHOT through the FIFO control queue and drops any unsent coalesced normal snapshot; it does not change snapshot wire format. Thus the final snapshot reaches the guest before result acknowledgement. Guest reads the explicit full-time marker and submits the same host/guest score. Both wait nonblockingly for `getResultStatus(matchId)==2` or 3 before LEAVE (the game adapter uses a bounded 3s wait). Getter status 0 means no response. Leaving/disconnecting before both matching attestations abandons the match and prevents later scoring. There is no post-disconnect attestation window or room resume. A broker restart marks all previously started but incomplete matches abandoned; the ledger still retains completed/conflicted/abandoned IDs. Escape, cancel, and interrupted matches never call the completion API.

Two-peer agreement prevents a lone connected participant from submitting the other player's stats, within this trusted host-simulation prototype. It does not establish accounts or validate the host's simulation against an independent guest simulation.

## Bounds and recovery

Broker: 128 clients, 64 rooms; per-peer writer queue 128 frames / 262144 bytes. Unsent snapshot frames coalesce to the latest, preserving queued control/input ordering. Other queue overflow closes that peer. Handshake 5s, complete payload 10s, idle next header 45s, writer drain 5s. Invalid framing closes before allocation; semantic command errors send ERROR. Closing a peer clears its queue and room ownership.

Java: at most 64 queued control/input/final-state frames / 131072 bytes, plus one latest outbound snapshot (60000 bytes); 64 inbound inputs plus latest inbound snapshot; 64 control events. ROOMS/LOBBY/CONNECTING/ERROR/LEADERBOARD/SELF_STATS/RESULT/PAUSE coalesce by event type. Inbound input overflow disconnects rather than silently losing button edges. Event overflow stops the session. Snapshot replacement is deliberate. Enqueued arrays are copied, so later caller changes cannot mutate an outgoing packet. Reads preserve partial headers and payloads across the 1s socket timeout. Handshake deadline 5s, inactivity 45s, blocked writer watchdog 5s, PING every 10s. The reader closes the socket to interrupt a blocked writer.

Connect/DNS run on a daemon, with a 15s visible timeout and automatic reconnect backoff 1s..10s. **Java 1.3 lacks a cancellable timed Socket.connect**: an OS/DNS call can outlive that deadline. At most one unresolved connector exists globally, including across repeated start/stop; further attempts wait/report the pending call instead of leaking connector threads. This can delay reconnection until the OS returns. Stop/start never waits on that I/O. All reconnects require manual room rejoin and ready again. Main-thread calls use only short in-memory synchronized sections.

## Verification

Use tools/test_online.py against a prepared workspace. The protocol suite has48
console tests: broker framing/rooms/ready, leaderboard persistence/attestations,
pause deadlines/automatic resume, malformed/truncated launcher handshakes,
mask3 rejection, mask7 success and species58. The guard suite has15 inert
process tests, including bootstrap handoff and eight concurrent starts.
An optional tests/real_broker_probe.py in the workspace uses the actual broker
CLI and production C++ health function on a temporary loopback port/ledger.
It never starts the game, changes a firewall or stops an existing service.

These checks do not establish two-PC Internet reachability, gameplay rendering,
input behavior or whole-game stability. Those require separate native tests.
