(function () {
  const cfg = window.SkillArenaPvp;
  if (!cfg || !window.WebSocket) {
    return;
  }

  const status = document.getElementById("liveStatus");
  const message = document.getElementById("liveMessage");
  const challengerScore = document.getElementById("liveChallengerScore");
  const opponentScore = document.getElementById("liveOpponentScore");
  const presence = document.getElementById("livePresence");
  const readyButton = document.getElementById("liveReadyButton");
  const readyCount = document.getElementById("liveReadyCount");
  const liveTimer = document.getElementById("liveTimer");
  const answerForm = document.getElementById("pvpAnswerForm");
  let roundInterval = null;
  let statePollInterval = null;
  let formSubmitted = false;
  let serverOffsetMs = 0;

  function setStatus(text) {
    if (status) {
      status.textContent = text;
    }
  }
  function setMessage(text) {
    if (message) {
      message.textContent = text;
    }
  }
  function setReadyCount(value) {
    if (readyCount) {
      readyCount.textContent = value;
    }
  }
  function setScores(data) {
    if (challengerScore && data.challenger_score !== undefined) {
      challengerScore.textContent = data.challenger_score;
    }
    if (opponentScore && data.opponent_score !== undefined) {
      opponentScore.textContent = data.opponent_score;
    }
  }
  function updateServerOffset(serverNow) {
    if (!serverNow) {
      return;
    }
    const parsed = Date.parse(serverNow);
    if (!Number.isNaN(parsed)) {
      serverOffsetMs = parsed - Date.now();
    }
  }
  function lockReadyButton(text) {
    if (readyButton) {
      readyButton.disabled = true;
      readyButton.textContent = text;
    }
  }
  function submitIfPossible() {
    if (formSubmitted || !answerForm) {
      return;
    }
    formSubmitted = true;
    const requiredRadios = answerForm.querySelectorAll(
      'input[type="radio"][required]',
    );
    requiredRadios.forEach((radio) => {
      const group = answerForm.querySelectorAll(`input[name="${radio.name}"]`);
      const checked = Array.from(group).some((item) => item.checked);
      if (!checked && group[0]) {
        group[0].checked = true;
      }
    });
    answerForm.submit();
  }
  function startDeadlineTimer(deadlineAt, fallbackSeconds) {
    let deadlineMs = Date.parse(deadlineAt || "");
    if (Number.isNaN(deadlineMs)) {
      deadlineMs = Date.now() + Number(fallbackSeconds || 60) * 1000;
    }
    if (roundInterval) {
      clearInterval(roundInterval);
    }
    const render = () => {
      const serverNowMs = Date.now() + serverOffsetMs;
      const remaining = Math.max(
        0,
        Math.ceil((deadlineMs - serverNowMs) / 1000),
      );
      if (liveTimer) {
        liveTimer.textContent = `${remaining}s`;
      }
      if (remaining <= 0) {
        clearInterval(roundInterval);
        setStatus("Time up");
        setMessage(
          "Server deadline reached. Submitting selected answers automatically.",
        );
        submitIfPossible();
      }
    };
    render();
    roundInterval = setInterval(render, 1000);
  }
  function applyStartedState(deadlineAt, serverNow, source) {
    if (!deadlineAt) {
      return;
    }
    updateServerOffset(serverNow);
    cfg.deadlineAt = deadlineAt;
    setStatus("Started");
    setMessage(source || "Server-timed battle is active.");
    lockReadyButton("Started");
    startDeadlineTimer(deadlineAt, 60);
  }
  function applyFinishedState(data) {
    setScores(data);
    setStatus("Finished");
    if (roundInterval) {
      clearInterval(roundInterval);
    }
    if (statePollInterval) {
      clearInterval(statePollInterval);
    }
    if (liveTimer) {
      liveTimer.textContent = "done";
    }
    if (data.winner_id === null || data.result === "tie") {
      setMessage("Battle finished as a tie. Entry fees refunded.");
    } else if (data.winner_id === cfg.userId) {
      setMessage("Battle finished. You won!");
    } else {
      setMessage("Battle finished. Opponent won.");
    }
  }
  async function pollBattleState() {
    try {
      const response = await fetch(`/pvp/${cfg.battleId}/state`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      updateServerOffset(data.server_now);
      setScores(data);
      if (data.status === "finished") {
        applyFinishedState(data);
        return;
      }
      if (data.deadline_at && !cfg.deadlineAt) {
        applyStartedState(
          data.deadline_at,
          data.server_now,
          "Recovered active server deadline.",
        );
      }
    } catch (e) {}
  }

  if (answerForm) {
    answerForm.addEventListener("submit", () => {
      formSubmitted = true;
    });
  }
  if (cfg.serverNow) {
    updateServerOffset(cfg.serverNow);
  }
  if (cfg.deadlineAt) {
    applyStartedState(
      cfg.deadlineAt,
      cfg.serverNow,
      "Battle already started. Timer is synchronized with the server deadline.",
    );
  }

  statePollInterval = setInterval(pollBattleState, 3000);
  setTimeout(pollBattleState, 700);

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(
    `${protocol}://${window.location.host}/pvp/${cfg.battleId}/ws`,
  );

  socket.addEventListener("open", () => {
    setStatus(cfg.deadlineAt ? "Started" : "Live");
    if (!cfg.deadlineAt) {
      setMessage(
        "Real-time channel connected. Press Ready when you are prepared.",
      );
    }
  });

  if (readyButton) {
    readyButton.addEventListener("click", () => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "ready" }));
        lockReadyButton("Ready ✓");
      } else {
        setMessage(
          "Live channel is not connected yet. Refresh the page and try again.",
        );
      }
    });
  }

  socket.addEventListener("close", () => {
    setStatus("Offline");
    setMessage(
      "Live channel closed. State polling is still watching the server deadline.",
    );
  });

  socket.addEventListener("message", (event) => {
    let data = {};
    try {
      data = JSON.parse(event.data);
    } catch (e) {
      return;
    }
    if (data.server_now) {
      updateServerOffset(data.server_now);
    }

    if (data.type === "connected") {
      if (data.deadline_at) {
        applyStartedState(
          data.deadline_at,
          data.server_now,
          "Connected to active server-timed battle.",
        );
      }
    }
    if (data.type === "presence") {
      if (presence) {
        presence.textContent = data.connections;
      }
      if (data.ready_count !== undefined) {
        setReadyCount(data.ready_count);
      }
      if (!cfg.deadlineAt) {
        setMessage(
          `${data.connections} player connection(s) in this battle room.`,
        );
      }
    }
    if (data.type === "ready") {
      if (data.ready_count !== undefined) {
        setReadyCount(data.ready_count);
      }
      setMessage("A player is ready in the live battle room.");
    }
    if (data.type === "battle_started") {
      applyStartedState(
        data.deadline_at,
        data.server_now,
        "Both players are ready. Server deadline started!",
      );
    }
    if (data.type === "opponent_joined") {
      setStatus("Opponent joined");
      setMessage(
        "Opponent joined. Battle is active. Press Ready when prepared.",
      );
    }
    if (data.type === "score_submitted") {
      setScores(data);
      setStatus("Score submitted");
      setMessage(
        data.late
          ? "Late submission recorded as zero by server deadline rules."
          : "A player submitted answers. Waiting for final result if needed.",
      );
    }
    if (data.type === "battle_finished") {
      applyFinishedState(data);
    }
  });
})();
