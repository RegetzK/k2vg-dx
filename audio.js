<script>
(function(){
  let ctx=null,started=false;
  const V=0.12; // master volume (0 to 1)

  function ac(){
    if(!ctx)ctx=new(window.AudioContext||window.webkitAudioContext)();
    if(ctx.state==='suspended')ctx.resume();
    return ctx;
  }

  function tone(f,t,d,type,g,dest){
    const c=ac(),o=c.createOscillator(),gn=c.createGain();
    o.type=type||'sine';o.frequency.setValueAtTime(f,t);
    gn.gain.setValueAtTime(g||V,t);
    o.connect(gn);gn.connect(dest||c.destination);
    o.start(t);o.stop(t+d);
  }

  function sweep(f1,f2,t,d,type,g){
    const c=ac(),o=c.createOscillator(),gn=c.createGain();
    o.type=type||'sine';
    o.frequency.setValueAtTime(f1,t);
    o.frequency.linearRampToValueAtTime(f2,t+d);
    gn.gain.setValueAtTime(g||V,t);
    gn.gain.linearRampToValueAtTime(0,t+d);
    o.connect(gn);gn.connect(c.destination);
    o.start(t);o.stop(t+d);
  }

  // --- AMBIENT LOOP (QRZ main page) ---
  function ambientLoop(){
    const c=ac(),t=c.currentTime;
    // Warp core hum (60+120+180Hz, very quiet)
    [60,120,180].forEach(f=>{
      const o=c.createOscillator(),gn=c.createGain();
      o.type='sine';o.frequency.value=f;
      gn.gain.value=V*0.15;
      o.connect(gn);gn.connect(c.destination);
      o.start(t);
    });
    // Random chirps every 2-4s
    function chirp(){
      if(!started)return;
      const f=300+Math.random()*600;
      tone(f,c.currentTime,0.04,'sine',V*0.08);
      setTimeout(chirp,2000+Math.random()*2000);
    }
    setTimeout(chirp,3000);
    // Data drips in clusters
    function drip(){
      if(!started)return;
      const n=3+Math.floor(Math.random()*3);
      for(let i=0;i<n;i++){
        tone(800+Math.random()*400,c.currentTime+i*0.08,0.02,'triangle',V*0.06);
      }
      setTimeout(drip,3000+Math.random()*3000);
    }
    setTimeout(drip,5000);
    // Power tick every 4s
    function tick(){
      if(!started)return;
      tone(1500,c.currentTime,0.015,'square',V*0.05);
      setTimeout(tick,4000);
    }
    setTimeout(tick,4000);
    // Sensor ping every 6s
    function ping(){
      if(!started)return;
      sweep(1200,200,c.currentTime,0.8,'sine',V*0.04);
      setTimeout(ping,6000);
    }
    setTimeout(ping,2000);
    // Timeline lock confirmation every 10s
    function lock(){
      if(!started)return;
      tone(440,c.currentTime,0.8,'sine',V*0.06);
      tone(660,c.currentTime,0.8,'sine',V*0.05);
      tone(1320,c.currentTime+0.2,0.6,'sine',V*0.03);
      setTimeout(lock,10000);
    }
    setTimeout(lock,10000);
  }

  // --- HAL ALERT (hal-alert.html) ---
  function halSequence(){
    const c=ac(),t=c.currentTime;
    // Omen rise (100→300Hz over 2s)
    sweep(100,300,t,2,'sine',V*0.2);
    // HAL hum (110+112Hz beat, 4s)
    const o1=c.createOscillator(),o2=c.createOscillator(),gn=c.createGain();
    o1.type='sine';o1.frequency.value=110;
    o2.type='sine';o2.frequency.value=112;
    gn.gain.value=V*0.15;
    o1.connect(gn);o2.connect(gn);gn.connect(c.destination);
    o1.start(t+2);o2.start(t+2);o1.stop(t+6);o2.stop(t+6);
    // Diagnostic ticks (3x 2kHz square, 50ms, 100ms gap)
    for(let i=0;i<3;i++){
      tone(2000,t+6.5+i*0.15,0.05,'square',V*0.3);
    }
    // Silence = the scare
  }

  // --- DESKTOP (unauthorized access) ---
  function alertKlaxon(){
    const c=ac(),t=c.currentTime;
    for(let i=0;i<4;i++){
      tone(440,t+i*0.8,0.4,'sawtooth',V*0.5);
      tone(554,t+i*0.8+0.4,0.4,'sawtooth',V*0.5);
    }
    tone(55,t,3.2,'sine',V*0.3);
  }

  function sonarBreach(){
    const c=ac(),t=c.currentTime;
    sweep(60,200,t,1.5,'sine',V*0.4);
    sweep(60,200,t+2,1.5,'sine',V*0.4);
    tone(40,t+4,2,'sine',V*0.3);
  }

  function allHands(){
    const c=ac(),t=c.currentTime;
    for(let i=0;i<3;i++){tone(280,t+i*0.3,0.25,'triangle',V*0.4)}
    for(let i=0;i<3;i++){tone(180,t+1.2+i*0.3,0.25,'triangle',V*0.4)}
  }

  function buzzerRumble(){
    const c=ac(),t=c.currentTime;
    for(let i=0;i<5;i++){tone(150,t+i*0.4,0.3,'sawtooth',V*0.5)}
    tone(35,t,2.5,'sine',V*0.3);
  }

  function subspaceLock(){
    const c=ac(),t=c.currentTime;
    const o=c.createOscillator(),gn=c.createGain();
    o.type='sine';o.frequency.value=220;
    gn.gain.setValueAtTime(0,t);
    gn.gain.linearRampToValueAtTime(V*0.15,t+2);
    o.connect(gn);gn.connect(c.destination);
    o.start(t);o.stop(t+4);
    tone(1400,t+2,0.1,'sine',V*0.2);
  }

  // --- PAGE DETECTION & AUTO-START ---
  function init(){
    started=true;
    const url=window.location.pathname;
    if(url.includes('hal-alert')){
      halSequence();
    } else if(url.includes('desktop')){
      subspaceLock();
    } else {
      ambientLoop();
    }
  }

  // Unlock on first interaction (browser requirement)
  document.addEventListener('click',function unlock(){
    if(!started){ac();init();}
    document.removeEventListener('click',unlock);
  },{once:true});

  // Expose for manual triggering (desktop.html unauthorized access)
  window.K2VGAudio={klaxon:alertKlaxon,sonar:sonarBreach,allHands:allHands,buzzer:buzzerRumble,lock:subspaceLock};
})();
</script>   
