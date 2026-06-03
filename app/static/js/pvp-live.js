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
  let formSubmitted = false;

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
  function startRoundTimer(seconds) {
    let remaining = Number(seconds || 60);
    if (roundInterval) {
      clearInterval(roundInterval);
    }
    const render = () => {
      if (liveTimer) {
        liveTimer.textContent = `${remaining}s`;
      }
    };
    render();
    roundInterval = setInterval(() => {
      remaining -= 1;
      render();
      if (remaining <= 0) {
        clearInterval(roundInterval);
        setStatus("Time up");
        setMessage(
          "Round timer ended. Submitting selected answers automatically.",
        );
        submitIfPossible();
      }
    }, 1000);
  }

  if (answerForm) {
    answerForm.addEventListener("submit", () => {
      formSubmitted = true;
    });
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(
    `${protocol}://${window.location.host}/pvp/${cfg.battleId}/ws`,
  );

  socket.addEventListener("open", () => {
    setStatus("Live");
    setMessage(
      "Real-time channel connected. Press Ready when you are prepared.",
    );
  });

  if (readyButton) {
    readyButton.addEventListener("click", () => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "ready" }));
        readyButton.disabled = true;
        readyButton.textContent = "Ready ✓";
      }
    });
  }

  socket.addEventListener("close", () => {
    setStatus("Offline");
    setMessage("Live channel closed. Refresh if you want live updates again.");
  });

  socket.addEventListener("message", (event) => {
    let data = {};
    try {
      data = JSON.parse(event.data);
    } catch (e) {
      return;
    }

    if (data.type === "presence") {
      if (presence) {
        presence.textContent = data.connections;
      }
      if (data.ready_count !== undefined) {
        setReadyCount(data.ready_count);
      }
      setMessage(
        `${data.connections} player connection(s) in this battle room.`,
      );
    }
    if (data.type === "ready") {
      if (data.ready_count !== undefined) {
        setReadyCount(data.ready_count);
      }
      setMessage("A player is ready in the live battle room.");
    }
    if (data.type === "battle_started") {
      setStatus("Started");
      setMessage("Both players are ready. Timer started!");
      startRoundTimer(data.duration_seconds || 60);
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
        "A player submitted answers. Waiting for final result if needed.",
      );
    }
    if (data.type === "battle_finished") {
      setScores(data);
      setStatus("Finished");
      if (roundInterval) {
        clearInterval(roundInterval);
      }
      if (liveTimer) {
        liveTimer.textContent = "done";
      }
      if (data.result === "tie") {
        setMessage("Battle finished as a tie. Entry fees refunded.");
      } else if (data.winner_id === cfg.userId) {
        setMessage("Battle finished. You won!");
      } else {
        setMessage("Battle finished. Opponent won.");
      }
    }
  });
})();
