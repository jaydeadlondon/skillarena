(function(){
    const cfg = window.SkillArenaLesson;
    if(!cfg){return;}
  
    const watchedInput = document.getElementById('watchedSeconds');
    const watchedMinutes = document.getElementById('watchedMinutes');
    const watchedPercent = document.getElementById('watchedPercent');
    const watchedProgress = document.getElementById('watchedProgress');
    const statusEl = document.getElementById('videoTrackingStatus');
    let localWatched = Number(cfg.watchedSeconds || 0);
    let pendingSeconds = 0;
    let isPlaying = false;
    let fallbackTracking = false;
  
    function isVisible(){ return document.visibilityState === 'visible'; }
  
    function setStatus(text){ if(statusEl){ statusEl.textContent = text; } }
  
    function render(){
      const percent = Math.min(100, Math.floor(localWatched * 100 / Math.max(cfg.durationSeconds, 1)));
      if(watchedInput){ watchedInput.value = String(localWatched); }
      if(watchedMinutes){ watchedMinutes.textContent = (localWatched / 60).toFixed(1); }
      if(watchedPercent){ watchedPercent.textContent = String(percent); }
      if(watchedProgress){ watchedProgress.style.width = `${percent}%`; }
    }
  
    function sendLessonHeartbeat(seconds){
      if(seconds <= 0){ return; }
      const payload = JSON.stringify({
        activity_type: 'lesson',
        seconds,
        reference_id: cfg.lessonId,
        path: window.location.pathname
      });
      fetch('/activity/heartbeat', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: payload,
        keepalive: true
      }).catch(()=>{});
    }
  
    function tick(){
      if((isPlaying || fallbackTracking) && isVisible()){
        localWatched += 5;
        pendingSeconds += 5;
        render();
        if(pendingSeconds >= 15){
          sendLessonHeartbeat(pendingSeconds);
          pendingSeconds = 0;
        }
      }
    }
  
    setInterval(tick, 5000);
    window.addEventListener('beforeunload', ()=>{
      if(pendingSeconds > 0){
        const payload = JSON.stringify({activity_type:'lesson', seconds: pendingSeconds, reference_id: cfg.lessonId, path: window.location.pathname});
        if(navigator.sendBeacon){navigator.sendBeacon('/activity/heartbeat', new Blob([payload], {type:'application/json'}));}
      }
    });
  
    if(cfg.provider === 'youtube'){
      setStatus('YouTube API loading');
      const tag = document.createElement('script');
      tag.src = 'https://www.youtube.com/iframe_api';
      document.head.appendChild(tag);
      window.onYouTubeIframeAPIReady = function(){
        const player = new YT.Player('lessonPlayer', {
          events: {
            onReady: function(){ setStatus('Ready — press play'); },
            onStateChange: function(event){
              if(event.data === YT.PlayerState.PLAYING){
                isPlaying = true;
                setStatus('Tracking playback');
              } else {
                isPlaying = false;
                if(pendingSeconds > 0){ sendLessonHeartbeat(pendingSeconds); pendingSeconds = 0; }
                if(event.data === YT.PlayerState.PAUSED){ setStatus('Paused'); }
                if(event.data === YT.PlayerState.ENDED){ setStatus('Video ended'); }
              }
            }
          }
        });
      };
    } else {
      setStatus('Manual fallback tracking');
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn';
      btn.textContent = 'Start fallback lesson timer';
      btn.addEventListener('click', ()=>{
        fallbackTracking = !fallbackTracking;
        btn.textContent = fallbackTracking ? 'Pause fallback lesson timer' : 'Start fallback lesson timer';
        setStatus(fallbackTracking ? 'Fallback tracking active' : 'Fallback tracking paused');
        if(!fallbackTracking && pendingSeconds > 0){ sendLessonHeartbeat(pendingSeconds); pendingSeconds = 0; }
      });
      const form = document.getElementById('progressForm');
      if(form){ form.parentNode.insertBefore(btn, form); }
    }
  
    render();
  })();
  