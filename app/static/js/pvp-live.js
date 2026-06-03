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
  function setScores(data) {
    if (challengerScore && data.challenger_score !== undefined) {
      challengerScore.textContent = data.challenger_score;
    }
    if (opponentScore && data.opponent_score !== undefined) {
      opponentScore.textContent = data.opponent_score;
    }
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(
    `${protocol}://${window.location.host}/pvp/${cfg.battleId}/ws`,
  );

  socket.addEventListener("open", () => {
    setStatus("Live");
    setMessage(
      "Real-time channel connected. You will see joins, submits, and final results here.",
    );
    socket.send(JSON.stringify({ type: "ready" }));
  });

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
      setMessage(
        `${data.connections} player connection(s) in this battle room.`,
      );
    }
    if (data.type === "ready") {
      setMessage("A player is ready in the live battle room.");
    }
    if (data.type === "opponent_joined") {
      setStatus("Opponent joined");
      setMessage("Opponent joined. Battle is active.");
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
