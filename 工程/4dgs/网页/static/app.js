/* Flow4DGS 4D 高斯实时预览前端
   视角策略：以该时刻的估计位姿为基准，允许在原机位小幅左右看/上下看/推拉；
   不做绕场景环绕（单目只观测了一个视锥，绕过去必然空洞）。 */
(() => {
  const WS_PORT = (location.port === '8770') ? '8771' : (Number(location.port || 80) + 1);
  const $ = (id) => document.getElementById(id);

  const canvas = $('view');
  const ctx = canvas.getContext('2d', { alpha: false });
  const video = $('inputVideo');

  const LIMIT = { yaw: 85, pitch: 65, dolly: 4 };
  let inputTicket = 0;
  let inputKey = '';
  function showInputs(name, idx) {
    const key = `${name}:${idx}`;
    if (key === inputKey) return Promise.resolve(null);
    inputKey = key;
    const ticket = ++inputTicket;
    const root = `/input-frame?model=${encodeURIComponent(name)}&i=${idx}&kind=`;
    const rgb = new Image(), depth = new Image();
    return Promise.all([new Promise((ok, fail) => { rgb.onload = ok; rgb.onerror = fail; rgb.src = root + 'rgb'; }),
                 new Promise((ok, fail) => { depth.onload = ok; depth.onerror = fail; depth.src = root + 'depth'; })])
      .then(() => ({rgb, depth, idx, ticket}));
  }

  const SEQ_LABEL = {
    full_xyz: 'walking_xyz（相机平移）',
    full_static: 'walking_static（相机静止）',
    full_sitting: 'sitting_static（两人坐着）',
    grow_static: 'walking_static（出生帧渐进回放）',
    full298: 'walking_xyz（原包模型）',
  };

  let videoName = '';

  function loadVideo(name) {
    if (!name || videoName === name) return;
    videoName = name;
    const inputName = name === 'grow_static' ? 'full_static' : name;
    const src = `input_${inputName}.mp4`;
    video.src = src;
    video.load();
  }

  const S = {
    t: 0, yaw: 0, pitch: 0, dolly: 0,
    mode: 'free', playing: false, speed: 1, growMode: 'birth',
    w: 640, h: 480, q: 85,
    inflight: false, dirty: false,
    lastHeader: null, ms: 0,
    scene: null, fps: 0, frames: 0, fpsT: performance.now(),
    idleTimer: null,
  };

  // ---------------- WebSocket ----------------
  let ws = null;
  let initialScene = true;
  function connect() {
    const url = `ws://${location.hostname || '127.0.0.1'}:${WS_PORT}`;
    ws = new WebSocket(url);
    ws.binaryType = 'arraybuffer';
    ws.onopen = () => { $('conn').classList.add('on'); ws.send(JSON.stringify({ type: 'hello' })); };
    ws.onclose = () => { S.inflight = false; S.dirty = false; $('conn').classList.remove('on'); setTimeout(connect, 1200); };
    ws.onerror = () => $('conn').classList.remove('on');
    ws.onmessage = (ev) => {
      if (typeof ev.data === 'string') {
        const h = JSON.parse(ev.data);
        if (h.type === 'scene') {
          S.inflight = false;
          if (initialScene) {
            initialScene = false;
            if (h.models && h.models.includes('grow_static') && h.name !== 'grow_static') {
              ws.send(JSON.stringify({type:'use', name:'grow_static'}));
              return;
            }
          }
          S.scene = h;
          if (h.name !== 'grow_static') S.growMode = 'off';
          $('growMode').value = S.growMode;
          $('kGauss').textContent = h.gaussians.toLocaleString();
          $('kKf').textContent = h.keyframes;
          $('kFrames').textContent = h.frames;
          $('frameNumber').max = h.frames - 1;
          if (h.models && h.models.length) {
            const sel = $('seqSel');
            const keep = h.name || (h.models.includes(sel.value) ? sel.value : h.models[0]);
            if (sel.options.length !== h.models.length) {
              sel.replaceChildren(...h.models.map((m) => new Option(SEQ_LABEL[m] || m, m)));
            }
            sel.value = keep;
          }
          loadVideo(h.name || 'full_xyz');
          $('seqMeta').textContent = `当前：${SEQ_LABEL[h.name] || h.name} · ${h.frames} 帧 · ${h.gaussians.toLocaleString()} 高斯 · ${h.keyframes} 关键帧`;
          requestRender();
        } else if (h.type === 'frame') {
          S.lastHeader = h;
          S.ms = h.ms;
          $('kMs').textContent = h.ms.toFixed(1) + ' ms';
          if (h.born != null && h.total) {
            $('bornBar').textContent = `高斯 ${h.born.toLocaleString()} / ${h.total.toLocaleString()}（${(h.born / h.total * 100).toFixed(1)}%）`;
          }
          syncVideo(h.t);
        }
      } else {
        const header = S.lastHeader, sceneName = S.scene.name;
        const blob = new Blob([ev.data], { type: 'image/jpeg' });
        Promise.all([createImageBitmap(blob), showInputs(sceneName, header.idx)]).then(([bmp, inputs]) => {
          if (S.scene.name !== sceneName) { bmp.close(); return; }
          if (inputs) {
            $('inputRgb').src = inputs.rgb.src; $('inputDepth').src = inputs.depth.src;
            $('inputCap').textContent = `RGB / Depth / 重建 · ${sceneName} · 源帧 ${header.idx}`;
          }
          const scale = Math.min(canvas.width / bmp.width, canvas.height / bmp.height);
          const dw = bmp.width * scale, dh = bmp.height * scale;
          ctx.fillStyle = '#0b0f13';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(bmp, (canvas.width - dw) / 2, (canvas.height - dh) / 2, dw, dh);
          bmp.close && bmp.close();
          S.frames++;
        }).catch(() => { inputKey = ''; $('inputCap').textContent = '输入加载失败，未提交本次画面'; })
          .finally(() => { S.inflight = false; if (S.dirty) { S.dirty = false; requestRender(); } });
      }
    };
  }

  function requestRender() {
    if (!ws || ws.readyState !== WebSocket.OPEN || !S.scene) return;
    if (S.inflight) { S.dirty = true; return; }
    S.inflight = true;
    ws.send(JSON.stringify({
      t: S.t, yaw: S.yaw, pitch: S.pitch, dolly: S.dolly,
      mode: S.mode, w: S.w, h: S.h, q: S.q,
      grow: S.growMode === 'birth', anim: S.growMode === 'anim',
    }));
  }

  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

  // ---------------- 交互 ----------------
  let dragging = false, lastX = 0, lastY = 0;
  canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  canvas.addEventListener('pointerdown', (e) => {
    dragging = true; lastX = e.clientX; lastY = e.clientY;
    canvas.setPointerCapture(e.pointerId);
    beginInteract();
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const dx = e.clientX - lastX, dy = e.clientY - lastY;
    lastX = e.clientX; lastY = e.clientY;
    S.yaw = clamp(S.yaw - dx * 0.15, -LIMIT.yaw, LIMIT.yaw);
    S.pitch = clamp(S.pitch + dy * 0.12, -LIMIT.pitch, LIMIT.pitch);
    requestRender();
  });
  canvas.addEventListener('pointerup', (e) => {
    dragging = false;
    canvas.releasePointerCapture(e.pointerId);
    endInteract();
  });
  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    S.dolly = clamp(S.dolly + Math.sign(e.deltaY) * 0.03, -LIMIT.dolly, LIMIT.dolly);
    beginInteract(); requestRender(); endInteract();
  }, { passive: false });

  function beginInteract() {
    S.w = 640; S.h = 480; S.q = 80;
    clearTimeout(S.idleTimer);
  }
  function endInteract() {
    clearTimeout(S.idleTimer);
    S.idleTimer = setTimeout(() => { S.w = 960; S.h = 720; S.q = 90; requestRender(); }, 450);
  }

  // ---------------- 时间轴 ----------------
  $('seek').addEventListener('input', (e) => {
    S.t = Number(e.target.value);
    updateTimeLabel();
    requestRender();
  });
  function stepFrame(delta) {
    if (!S.scene) return;
    S.playing = false; video.pause(); $('btnPlay').textContent = '播放';
    const last = S.scene.frames - 1;
    S.t = clamp(Math.round(S.t * last) + delta, 0, last) / last;
    updateTimeLabel(); requestRender();
  }
  $('prevFrame').addEventListener('click', () => stepFrame(-1));
  $('nextFrame').addEventListener('click', () => stepFrame(1));
  $('frameNumber').addEventListener('change', (e) => {
    if (!S.scene) return;
    const idx = Number(e.target.value);
    if (!Number.isFinite(idx)) return;
    S.playing = false; video.pause(); $('btnPlay').textContent = '播放';
    e.target.value = clamp(Math.round(idx), 0, S.scene.frames - 1);
    S.t = Number(e.target.value) / (S.scene.frames - 1);
    updateTimeLabel(); requestRender();
  });
  function updateTimeLabel() {
    if (S.scene && document.activeElement !== $('frameNumber')) $('frameNumber').value = Math.round(S.t * (S.scene.frames - 1));
    $('tval').textContent = (S.t * (videoReady() ? video.duration : 9.93)).toFixed(2) + ' s';
    $('seek').value = S.t;
  }

  $('btnPlay').addEventListener('click', () => {
    S.playing = !S.playing;
    $('btnPlay').textContent = S.playing ? '暂停' : '播放';
    if (S.playing) video.play().catch(() => {}); else video.pause();
  });
  $('speed').addEventListener('change', (e) => { S.speed = Number(e.target.value); video.playbackRate = S.speed; });
  $('btnReset').addEventListener('click', () => {
    S.yaw = 0; S.pitch = 0; S.dolly = 0; S.t = 0;
    updateTimeLabel(); requestRender();
  });
  $('btnOverview').addEventListener('click', () => {
    S.mode = 'free'; S.yaw = 0; S.pitch = 0; S.dolly = -1.2;
    setMode('free');
  });

  $('seqSel').addEventListener('change', (e) => {    const name = e.target.value;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    S.t = 0; S.yaw = 0; S.pitch = 0; S.dolly = 0;
    S.playing = false; video.pause(); $('btnPlay').textContent = '播放';
    S.growMode = name === 'grow_static' ? 'birth' : 'off';
    S.inflight = false;
    updateTimeLabel();
    $('seqMeta').textContent = '切换中…（首次加载约 15 秒）';
    ws.send(JSON.stringify({ type: 'use', name }));
  });

  $('growMode').addEventListener('change', (e) => {
    S.growMode = e.target.value;
    if (S.growMode === 'off') $('bornBar').textContent = '高斯 — / —';
    requestRender();
  });

  $('mOrbit').addEventListener('click', () => setMode('free'));
  $('mTraj').addEventListener('click', () => setMode('traj'));
  function setMode(m) {
    S.mode = m;
    $('mOrbit').classList.toggle('active', m === 'free');
    $('mTraj').classList.toggle('active', m === 'traj');
    $('hint').textContent = (m === 'free')
      ? '拖拽转向 ±85°/±65° · 滚轮推拉 ±4 m · 拉远看整体；观测外可能有空洞'
      : '沿估计轨迹回放（相机位姿来自跟踪结果）';
    requestRender();
  }

  $('btnFull').addEventListener('click', () => {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen();
    else document.exitFullscreen();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'f' || e.key === 'F') document.body.classList.toggle('clean');
  });

  // ---------------- 视频同步（视频为主时钟） ----------------
  function videoReady() {
    return video.readyState >= 2 && isFinite(video.duration) && video.duration > 0.1;
  }
  function syncVideo(t) {
    if (!videoReady() || S.playing) return;      // 播放时由视频驱动，不回写
    const target = t * video.duration;
    if (Math.abs(video.currentTime - target) > 0.12) video.currentTime = target;
  }

  // ---------------- 主循环 ----------------
  function fit() {
    const r = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(r.width * dpr);
    canvas.height = Math.round(r.height * dpr);
  }
  window.addEventListener('resize', fit);

  let prev = performance.now();
  function loop(now) {
    const dt = Math.min((now - prev) / 1000, 0.1);
    prev = now;
    if (S.playing && S.scene) {
      if (videoReady()) {
        S.t = Math.min(video.currentTime / video.duration, 0.999);
      } else {
        S.t += dt * S.speed * 0.1;
        if (S.t >= 1) S.t = 0;
      }
      updateTimeLabel();
      if (!S.inflight) requestRender();
    }
    if (now - S.fpsT > 800) {
      S.fps = S.frames * 1000 / (now - S.fpsT);
      S.frames = 0; S.fpsT = now;
      $('kFps').textContent = S.fps.toFixed(1) + ' fps';
      const h = S.lastHeader;
      $('stats').textContent = h
        ? `时间 ${(h.t * (videoReady() ? video.duration : 9.93)).toFixed(2)}s · ${h.w}×${h.h} · 渲染 ${h.ms.toFixed(1)} ms · 显示 ${S.fps.toFixed(0)} fps`
        : '等待首帧…';
    }
    requestAnimationFrame(loop);
  }

  fit();
  connect();
  setMode('free');
  requestAnimationFrame(loop);
})();
